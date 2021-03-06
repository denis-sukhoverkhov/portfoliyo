from django.conf.urls.defaults import patterns, url, include

from . import views

per_student_patterns = patterns(
    '',
    url(r'^invite/teacher/$', views.invite_teacher, name='invite_teacher'),
    url(r'^invite/family/$', views.invite_family, name='invite_family'),
    url(r'^edit/$', views.edit_student, name='edit_student'),
    url(r'^elder/(?P<elder_id>\d+)/$',
        views.edit_elder,
        name='edit_elder',
        ),
    url(r'^$', views.village, name='village'),
    url(r'^_post/$', views.create_post, name='create_post'),
    )


per_group_patterns = patterns(
    '',
    url(r'^$', views.dashboard, name='group_dash'),
    url(r'^post/$', views.group, name='group'),
    url(r'^invite/teacher/$',
        views.invite_teacher_to_group,
        name='invite_teacher',
        ),
    url(r'^edit/$', views.edit_group, name='edit_group'),
    url(r'^elder/(?P<elder_id>\d+)/$',
        views.edit_elder,
        name='edit_elder',
        ),
    url(r'^add/$', views.add_student, name='add_student'),
    url(r'^_post/$', views.create_post, name='create_post'),
    url(r'^instructions-(?P<lang>en|es).pdf$',
        views.pdf_parent_instructions,
        name='pdf_parent_instructions',
        ),
    )


urlpatterns = patterns(
    '',
    url(r'^$', views.dashboard, name='all_students_dash'),
    url(r'^add/$', views.add_student, name='add_student'),
    url(r'^(?P<student_id>\d+)/', include(per_student_patterns)),
    url(r'^all/$', views.group, name='all_students'),
    url(r'^all/_post/$', views.create_post, name='create_post'),
    url(r'^elder/(?P<elder_id>\d+)/$', views.edit_elder, name='edit_elder'),
    url(r'^group/add/$', views.add_group, name='add_group'),
    url(r'^group/(?P<group_id>\d+)/', include(per_group_patterns)),
    url(r'^instructions-(?P<lang>en|es).pdf$',
        views.pdf_parent_instructions,
        name='pdf_parent_instructions',
        ),
    url(r'^_mark_read/(?P<post_id>\d+)/',
        views.mark_post_read,
        name='mark_post_read',
        ),
    )
