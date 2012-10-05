from django.conf.urls.defaults import patterns, url, include

from . import views

per_student_patterns = patterns(
    '',
    url(r'^invite/$', views.invite_elders, name='invite_elders'),
    url(r'^edit/$', views.edit_student, name='edit_student'),
    url(r'^elder/(?P<elder_id>\d+)/$', views.edit_elder, name='edit_elder'),
    url(r'^$', views.village, name='village'),
    url(r'^_posts/$', views.json_posts, name='json_posts'),
    )


urlpatterns = patterns(
    '',
    url(r'^$', views.dashboard, name='dashboard'),
    url(r'^add/$', views.add_student, name='add_student'),
    url(r'^instructions-(?P<lang>en|es).pdf$',
        views.pdf_parent_instructions,
        name='pdf_parent_instructions',
        ),
    url(r'^(?P<student_id>\d+)/', include(per_student_patterns)),
    )
