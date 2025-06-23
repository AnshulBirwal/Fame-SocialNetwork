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


    is_community_mode = request.session['community_mode']  #read mode from session
    available_communities_not_joined = [] # by default empty. Stays empty in standard mode,
                                          # will be appended in community mode
    if is_community_mode: #getting communities to show for both modes
        communities_joined_to_show = list(user.communities.all().values_list("label", flat=True))

        eligible_communities = (Fame.objects.filter(user=user, fame_level__numeric_value__gte=100). all()
                                .values_list("expertise_area", flat=True)) #100 is super pro
        for potential_community in eligible_communities:
            if potential_community not in communities_joined_to_show:
                available_communities_not_joined.append(potential_community)
    else:
        communities_joined_to_show = [] #user.communities.none().values_list("label") #empty, because none()

    # get extra URL parameters:
    keyword = request.GET.get("search", "")
    published = request.GET.get("published", True)
    error = request.GET.get("error", None)

    # if keyword is not empty, use search method of API:
    if keyword and keyword != "":
        context = {
            "communities_joined": communities_joined_to_show,
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
            "communities_joined": communities_joined_to_show,
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
@require_http_methods(["GET"])
@login_required
def bullshitters(request):
    raise NotImplementedError("Not implemented yet")


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
    com = request.POST.get("community")
    community = ExpertiseAreas.objects.get(label=com)
    user = SocialNetworkUsers.objects.get(user=request.user)
    api.join_community(user, community)
    return redirect(reverse("sn:timeline"))

@require_http_methods(["POST"])
@login_required
def leave_community(request):
    com=request.POST.get("community")
    community = ExpertiseAreas.objects.get(label = com)
    user = SocialNetworkUsers.objects.get(user = request.user)
    api.leave_community(user, community)
    return redirect(reverse("sn:timeline"))



#T8
@require_http_methods(["GET"])
@login_required
def similar_users(request):
    raise NotImplementedError("Not implemented yet")
