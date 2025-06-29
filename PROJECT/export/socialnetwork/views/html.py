from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from socialnetwork import api
from socialnetwork.api import _get_social_network_user
from socialnetwork.models import SocialNetworkUsers
from socialnetwork.serializers import PostsSerializer
from fame.models import Fame, ExpertiseAreas


@require_http_methods(["GET", "POST"])
@login_required
def timeline(request):
    # using the serializer to get the data, then use JSON in the template!
    # avoids having to do the same thing twice
    user=_get_social_network_user(request.user)
    # initialize community mode to False the first time in the session
    if 'community_mode' not in request.session:
        request.session['community_mode'] = False
        #same for bullshitters mode
    if 'bullshitters_mode' not in request.session:
        request.session['bullshitters_mode'] = False

    if 'similar_users_mode' not in request.session:
        request.session['similar_users_mode'] = False

    is_community_mode = request.session['community_mode']  #read mode from session
    show_bullshitters_mode = request.session['bullshitters_mode']  # read mode from session
    show_similar_users_mode = request.session['similar_users_mode']  # read mode from session

    communities_joined = []
    available_communities_not_joined = [] # by default empty
    if is_community_mode:
        communities_joined = list(user.communities.all().values_list("label", flat=True).distinct())

        #this will be a list of IDs(!) of corresponding expertise areas
        eligible_communities_area_ids = list(Fame.objects.filter(user=user, fame_level__numeric_value__gte=100).all()
                                .values_list("expertise_area_id", flat=True).distinct()) #100 is super pro

        #now again we want a list with labels instead of IDs
        for potential_community_area_id in eligible_communities_area_ids:
            potential_community_name = (ExpertiseAreas.objects.filter(id=potential_community_area_id)
                                        .values_list("label", flat=True).first()) #first element of the queryset (and the only one)
            #expertiseareas is an automatically generated field, because it's foreign key in communities

            if (potential_community_name not in communities_joined
                    and potential_community_name not in available_communities_not_joined): #we don't want the same community twice
                    available_communities_not_joined.append(potential_community_name)
    #if standard mode, the communities lists will stay empty.
    #We could still fill them with respective communities because we built timeline.html the way
    #that it doesn't show the communities in standard mode
    #but for performance it will be better not to fill the communities in standard mode

    bullshitters_dict={}
    if show_bullshitters_mode: #getting the actual dictionary only if the user asked for it (better performance)
        bullshitters_dict = api.bullshitters()

    similar_users_list = []
    if show_similar_users_mode:  # getting the actual list only if the user asked for it (better performance)
        similar_users_list = api.similar_users(user)

    # get extra URL parameters:
    keyword = request.GET.get("search", "")
    published = request.GET.get("published", True)
    error = request.GET.get("error", None)


    # if keyword is not empty, use search method of API:
    if keyword and keyword != "":
        context = {
            "similar_users": similar_users_list,
            "bullshitters": bullshitters_dict,
            "communities_joined": communities_joined,
            "available_communities_not_joined": available_communities_not_joined,
            "posts": PostsSerializer(
                api.search(keyword, published=published), many=True
            ).data, #so far I am not changing it
            "searchkeyword": keyword,
            "error": error,
            "followers": list(api.follows(user).values_list('id', flat=True)),
        }
    else:  # otherwise, use timeline method of API:
        context = {
            "similar_users": similar_users_list,
            "bullshitters": bullshitters_dict,
            "communities_joined": communities_joined,
            "available_communities_not_joined": available_communities_not_joined,
            "posts": PostsSerializer(
                api.timeline(
                    user,
                    published=published,
                    community_mode=is_community_mode
                ),
                many=True,
            ).data,
            "searchkeyword": "",
            "error": error,
            "followers": list(api.follows(user).values_list('id', flat=True)),
        }
    return render(request, "timeline.html", context=context)

@require_http_methods(["POST"])
@login_required
def follow(request):
    user = _get_social_network_user(request.user)
    user_to_follow = SocialNetworkUsers.objects.get(id=request.POST.get("user_id"))
    api.follow(user, user_to_follow)
    return redirect(reverse("sn:timeline"))


@require_http_methods(["POST"])
@login_required
def unfollow(request):
    user = _get_social_network_user(request.user)
    user_to_unfollow = SocialNetworkUsers.objects.get(id=request.POST.get("user_id"))
    api.unfollow(user, user_to_unfollow)
    return redirect(reverse("sn:timeline"))


#T6
#we will "toggle" bullshitters mode (the button either shows or hides the list
@require_http_methods(["GET"])
@login_required
def bullshitters(request):
    current = request.session.get("bullshitters_mode", False)  # false is default
    request.session["bullshitters_mode"] = not current
    return redirect(reverse("sn:timeline"))  # redirect back to timeline after toggling


#T7
@require_http_methods(["POST"])
@login_required
def toggle_community_mode(request):
    current = request.session.get("community_mode", False) #false is default
    request.session["community_mode"] = not current
    return redirect(reverse("sn:timeline"))  # redirect back to timeline after toggling


@require_http_methods(["POST"])
@login_required
def join_community(request):
    community_name = request.POST.get("community")
    community = ExpertiseAreas.objects.get(label=community_name)
    user = _get_social_network_user(request.user)
    api.join_community(user, community)
    return redirect(reverse("sn:timeline"))

@require_http_methods(["POST"])
@login_required
def leave_community(request):
    community_name=request.POST.get("community")
    community = ExpertiseAreas.objects.get(label = community_name)
    user = _get_social_network_user(request.user)
    api.leave_community(user, community)
    return redirect(reverse("sn:timeline"))

#T8
@require_http_methods(["GET"])
@login_required
def similar_users(request):
    current = request.session.get("similar_users_mode", False)  # false is default
    request.session["similar_users_mode"] = not current
    return redirect(reverse("sn:timeline"))  # redirect back to timeline after toggling
