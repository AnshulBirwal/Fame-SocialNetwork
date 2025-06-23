from django.db.models import Q, Exists, OuterRef, When, IntegerField, FloatField, Count, ExpressionWrapper, Case, Value, F, Prefetch

from fame.models import Fame, FameLevels, FameUsers, ExpertiseAreas
from socialnetwork.models import Posts, SocialNetworkUsers


# general methods independent of html and REST views
# should be used by REST and html views


def _get_social_network_user(user) -> SocialNetworkUsers:
    """Given a FameUser, gets the social network user from the request. Assumes that the user is authenticated."""
    try:
        user = SocialNetworkUsers.objects.get(id=user.id)
    except SocialNetworkUsers.DoesNotExist:
        raise PermissionError("User does not exist")
    return user


def timeline(user: SocialNetworkUsers, start: int = 0, end: int = None, published=True, community_mode=False):
    """Get the timeline of the user. Assumes that the user is authenticated."""

    if community_mode:
        # T4
        # in community mode, posts of communities are displayed if ALL of the following criteria are met:
        # 1. the author of the post is a member of the community
        # 2. the user is a member of the community
        # 3. the post contains the community’s expertise area
        # 4. the post is published or the user is the author

        posts=[] #temporary line just to get rid of the error!!!
        #########################
        # add your code here
        #########################

        #_communities_of_user = user.communities # 2. the user is a member of the community


    else:
        # in standard mode, posts of followed users are displayed
        _follows = user.follows.all()
        posts = Posts.objects.filter(
            (Q(author__in=_follows) & Q(published=published)) | Q(author=user)
        ).order_by("-submitted")
    if end is None:
        return posts[start:]
    else:
        return posts[start:end+1]


def search(keyword: str, start: int = 0, end: int = None, published=True):
    """Search for all posts in the system containing the keyword. Assumes that all posts are public"""
    posts = Posts.objects.filter(
        Q(content__icontains=keyword)
        | Q(author__email__icontains=keyword)
        | Q(author__first_name__icontains=keyword)
        | Q(author__last_name__icontains=keyword),
        published=published,
    ).order_by("-submitted")
    if end is None:
        return posts[start:]
    else:
        return posts[start:end+1]


def follows(user: SocialNetworkUsers, start: int = 0, end: int = None):
    """Get the users followed by this user. Assumes that the user is authenticated."""
    _follows = user.follows.all()
    if end is None:
        return _follows[start:]
    else:
        return _follows[start:end+1]


def followers(user: SocialNetworkUsers, start: int = 0, end: int = None):
    """Get the followers of this user. Assumes that the user is authenticated."""
    _followers = user.followed_by.all()
    if end is None:
        return _followers[start:]
    else:
        return _followers[start:end+1]


def follow(user: SocialNetworkUsers, user_to_follow: SocialNetworkUsers):
    """Follow a user. Assumes that the user is authenticated. If user already follows the user, signal that."""
    if user_to_follow in user.follows.all():
        return {"followed": False}
    user.follows.add(user_to_follow)
    user.save()
    return {"followed": True}


def unfollow(user: SocialNetworkUsers, user_to_unfollow: SocialNetworkUsers):
    """Unfollow a user. Assumes that the user is authenticated. If user does not follow the user anyway, signal that."""
    if user_to_unfollow not in user.follows.all():
        return {"unfollowed": False}
    user.follows.remove(user_to_unfollow)
    user.save()
    return {"unfollowed": True}


def submit_post(
    user: SocialNetworkUsers,
    content: str,
    cites: Posts = None,
    replies_to: Posts = None,
):
    """Submit a post for publication. Assumes that the user is authenticated.
    returns a tuple of three elements:
    1. a dictionary with the keys "published" and "id" (the id of the post)
    2. a list of dictionaries containing the expertise areas and their truth ratings
    3. a boolean indicating whether the user was banned and logged out and should be redirected to the login page
    """

    # create post  instance:
    post = Posts.objects.create(
        content=content,
        author=user,
        cites=cites,
        replies_to=replies_to,
    )

    # classify the content into expertise areas:
    # only publish the post if none of the expertise areas contains bullshit:
    _at_least_one_expertise_area_contains_bullshit, _expertise_areas = (
        post.determine_expertise_areas_and_truth_ratings()
    )
    post.published = not _at_least_one_expertise_area_contains_bullshit #the first condition

    redirect_to_logout = False


    #########################
    # add your code here
    #########################
    #T1
    #Change api.submit_post to not publish posts that have an expertise area which is contained in
    #the user’s fame profile and marked negative there (independent of any truth rating determined by
    #the magic AI for this post)

    #the idea is for all expertise areas in the post (there are 2 of them normally) check if any of them is
    #among user's negative areas. If yes, don't publish
    _no_negative_areas = True
    user, _fame_of_user = fame(user)          #fame function returns user and their fames (fame contains user, expertise_area and fame_level)
    negative_fames = _fame_of_user.filter(fame_level__numeric_value__lt=0)
    _negative_expertise_areas_of_user = [fame_entry.expertise_area for fame_entry in negative_fames]   #we are only interested in expertise areas from fames
    _expertise_areas_without_levels = [entry['expertise_area'] for entry in _expertise_areas]          #from areas from post we also only choose areas
    for area in _expertise_areas:
        if area['expertise_area'] in _negative_expertise_areas_of_user:
            _no_negative_areas = False

    post.published = post.published and _no_negative_areas  # modified condition of publishing based on T1

        #T2 Change api.submit_post to adjust the fame profile of users if they submit a post with a negative
    #truth rating, but only for the expertise area found for the post that has a negative truth rating:
        #T2a If the expertise area is already contained in the user’s fame profile (with any fame level), lower
    #the fame to the next possible level.
        #T2b If the expertise area is not contained, simply add an entry in the user’s fame profile with fame
    #level “Confuser” (hint: negative fame and take a look at famesocialnetwork/fakedata.py).
        #T2c If you cannot lower the existing fame level for that expertise area any further, ban the user from
    #the social network by setting the field is_active in model FameUsers to False disallowing
    #him/her to ever login again, logging out the user if he or she is logged in, and unpublishing all
    #his/her posts (without deleting them from the database)

    #we need to lower the level only if at least one area is negative
    if _at_least_one_expertise_area_contains_bullshit:
        for area in _expertise_areas:
            _truth_rating_of_area = area['truth_rating']
            if _truth_rating_of_area: #if it is not none (aka if it is not unknown)
                if area['truth_rating'].numeric_value<0:
                    try:           #if the user already has this area in the profile
                        _fame_to_update = Fame.objects.get(expertise_area=area['expertise_area'], user=post.author)   #getting the fame we need
                        try:       #if possible to lower the level
                            _new_fame_level = _fame_to_update.fame_level.get_next_lower_fame_level()
                            _fame_to_update.fame_level = _new_fame_level

                        except ValueError:    #if impossible to lower the level BAN (get_next_lower_fame_level() will raise the error)
                            user.is_active=False
                            user.save()
                            redirect_to_logout=True
                            #unpublish all the posts of the user without deleting from db:
                            _posts_to_unpublish = Posts.objects.filter(author=user).update(published=False)

                        _fame_to_update.save()

                    except Fame.DoesNotExist:    #if the fame doesn't exist (the get method throws an exception)
                        _new_fame = Fame(expertise_area=area['expertise_area'],
                                         user=post.author,
                                         fame_level=FameLevels.objects.get(name='Confuser'))

                        _new_fame.save()
    post.save()

    return (
        {"published": post.published, "id": post.id},
        _expertise_areas,
        redirect_to_logout,
    )


def rate_post(
    user: SocialNetworkUsers, post: Posts, rating_type: str, rating_score: int
):
    """Rate a post. Assumes that the user is authenticated. If user already rated the post with the given rating_type,
    update that rating score."""
    user_rating = None
    try:
        user_rating = user.userratings_set.get(post=post, rating_type=rating_type)
    except user.userratings_set.model.DoesNotExist:
        pass

    if user == post.author:
        raise PermissionError(
            "User is the author of the post. You cannot rate your own post."
        )

    if user_rating is not None:
        # update the existing rating:
        user_rating.rating_score = rating_score
        user_rating.save()
        return {"rated": True, "type": "update"}
    else:
        # create a new rating:
        user.userratings_set.add(
            post,
            through_defaults={"rating_type": rating_type, "rating_score": rating_score},
        )
        user.save()
        return {"rated": True, "type": "new"}


def fame(user: SocialNetworkUsers):
    """Get the fame of a user. Assumes that the user is authenticated."""
    try:
        user = SocialNetworkUsers.objects.get(id=user.id)
    except SocialNetworkUsers.DoesNotExist:
        raise ValueError("User does not exist")

    return user, Fame.objects.filter(user=user)


def bullshitters():
    """Return a Python dictionary mapping each existing expertise area in the fame profiles to a list of the users
    having negative fame for that expertise area. Each list should contain Python dictionaries as entries with keys
    ``user'' (for the user) and ``fame_level_numeric'' (for the corresponding fame value), and should be ranked, i.e.,
    users with the lowest fame are shown first, in case there is a tie, within that tie sort by date_joined
    (most recent first). Note that expertise areas with no expert may be omitted.
    """
    #########################
    # add your code here

    result = {}

    # Filter Fame entries with negative fame levels
    negative_fames = (
        Fame.objects
        .select_related('user', 'fame_level', 'expertise_area')
        .filter(fame_level__numeric_value__lt=0)
    )

    # GROUP BY expertise area
    for fame_entry in negative_fames:
        user = fame_entry.user
        area = fame_entry.expertise_area
        fame_value = fame_entry.fame_level.numeric_value

            #add all the keys (expertise areas) to the list if not already present + append user ect.
        if area not in result: # this would be nicer (without if check) using defaultdict(list) but I'm not sure if we can import stuff ?
            result[area] = []

        result[area].append({
            "user": user,
            "fame_level_numeric": fame_value,
            "date_joined": user.date_joined
        })

    # Sort each list by fame_level_numeric ASC, then date_joined DESC
    for area in result:
        result[area].sort(
            key=lambda x: (x["fame_level_numeric"], -x["date_joined"].timestamp())
        )

        # Remove date_joined (used only for sorting) like a SELECT user, fame_level_numeric
        for entry in result[area]:
            del entry["date_joined"]

    return result
    #########################





def join_community(user: SocialNetworkUsers, community: ExpertiseAreas):
    """Join a specified community. Note that this method does not check whether the user is eligible for joining the
    community.
    """
    user.communities.add(community) # could also be community.community_members.add(user) (related_name) since it's anytomany so changing either side works
    #########################
    # add your code here
    #########################



def leave_community(user: SocialNetworkUsers, community: ExpertiseAreas):
    """Leave a specified community."""
    user.communities.remove(community)
    #########################
    # add your code here
    #########################



def similar_users(user: SocialNetworkUsers):
    """Compute the similarity of user with all other users. The method returns a QuerySet of FameUsers annotated
    with an additional field 'similarity'. Sort the result in descending order according to 'similarity', in case
    there is a tie, within that tie sort by date_joined (most recent first)"""
    pass
    #########################
    # add your code here
    #########################

