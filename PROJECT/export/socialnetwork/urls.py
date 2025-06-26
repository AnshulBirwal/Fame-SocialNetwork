from django.urls import path

from socialnetwork.views.html import timeline, toggle_community_mode, join_community, leave_community, bullshitters
from socialnetwork.views.html import follow
from socialnetwork.views.html import unfollow
from socialnetwork.views.rest import PostsListApiView

app_name = "socialnetwork"

urlpatterns = [
    path("api/posts", PostsListApiView.as_view(), name="posts_fulllist"),
    path("html/timeline", timeline, name="timeline"),
    path("html/toggle_community_mode", toggle_community_mode, name="toggle_community_mode"),
    path("html/bullshitters", bullshitters, name="bullshitters"),
    path("html/join_community", join_community, name="join_community"),
    path("html/leave_community", leave_community, name="leave_community"),
    path("api/follow", follow, name="follow"),
    path("api/unfollow", unfollow, name="unfollow"),
]
