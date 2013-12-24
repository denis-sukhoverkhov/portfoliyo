# -*- coding: utf-8 -*-
"""Tests for village views."""
import datetime

from django.core import mail
from django.core.urlresolvers import reverse
import mock
import pytest

from portfoliyo import model
from portfoliyo.model import unread
from portfoliyo.tests import factories, utils
from portfoliyo.view.village import views



class GroupContextTests(object):
    """Common tests for views that maintain group context via querystring."""
    def test_maintain_group_context(self, client):
        """Can take ?group=id to maintain group nav context."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        group = factories.GroupFactory.create(owner=rel.elder)
        group.students.add(rel.student)

        response = client.get(
            self.url(rel.student) + '?group=%s' % group.id,
            user=rel.elder.user,
            )

        assert response.context['group'] == group


    def test_group_context_student_must_be_in_group(self, client):
        """?group=id not effective unless student is in group."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        group = factories.GroupFactory.create(owner=rel.elder)

        response = client.get(
            self.url(rel.student) + '?group=%s' % group.id,
            user=rel.elder.user,
            )

        assert response.context['group'] is None


    def test_group_context_must_own_group(self, client):
        """?group=id not effective unless active user owns group."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        group = factories.GroupFactory.create()
        group.students.add(rel.student)

        response = client.get(
            self.url(rel.student) + '?group=%s' % group.id,
            user=rel.elder.user,
            )

        assert response.context['group'] is None


    def test_group_context_bad_id(self, client):
        """?group=id doesn't blow up with non-int id."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)

        response = client.get(
            self.url(rel.student) + '?group=all23',
            user=rel.elder.user,
            )

        assert response.context['group'] is None



class TestDashboard(object):
    def test_all_students_group(self, client):
        """Dashboard contains group name, student/teacher/family count."""
        rel = factories.RelationshipFactory(
            from_profile__school_staff=True, to_profile__name="Student Two")
        factories.RelationshipFactory(
            from_profile=rel.elder, to_profile__name="Student One")
        response = client.get(
            reverse('all_students_dash'), user=rel.elder.user, status=200)

        response.mustcontain("All Students")
        response.mustcontain("<b>2</b> Students")
        response.mustcontain("<b>1</b> Teacher")
        response.mustcontain("<b>0</b> Family Members")


    def test_group_dashboard(self, client):
        """Group dashboard contains group name, student/teacher/family count."""
        group = factories.GroupFactory.create(
            owner__school_staff=True, name="Some Group")
        rel = factories.RelationshipFactory(
            from_profile=group.owner, to_profile__name="Student Two")
        factories.RelationshipFactory(to_profile=rel.student)
        factories.RelationshipFactory(
            from_profile__school_staff=True, to_profile=rel.student)
        group.students.add(rel.student)
        response = client.get(
            reverse('group_dash', kwargs={'group_id': group.id}),
            user=group.owner.user,
            status=200,
            )

        response.mustcontain("Some Group")
        response.mustcontain("<b>1</b> Student")
        response.mustcontain("<b>2</b> Teachers")
        response.mustcontain("<b>1</b> Family Member")



class TestAddStudent(object):
    def test_contains_pdf_link(self, client):
        """Add student page contains link to parent instructions PDF."""
        p = factories.ProfileFactory.create(code='ABCDEF', school_staff=True)
        pdf_link = reverse('pdf_parent_instructions', kwargs={'lang': 'en'})
        response = client.get(reverse('add_student'), user=p.user)

        assert len(response.html.findAll('a', href=pdf_link))


    def test_contains_group_pdf_link(self, client):
        """Group add student page has link to parent instructions PDF."""
        g = factories.GroupFactory.create(
            code='ABCDEF', owner__school_staff=True)
        pdf_link = reverse(
            'pdf_parent_instructions', kwargs={'lang': 'es', 'group_id': g.id})
        response = client.get(
            reverse('add_student', kwargs={'group_id': g.id}),
            user=g.owner.user,
            )

        assert len(response.html.findAll('a', href=pdf_link))


    def test_steps_guide(self, client):
        """Two-step group-creation guide appears if requested in querystring."""
        g = factories.GroupFactory.create(owner__school_staff=True)
        normal_response = client.get(
            reverse('add_student', kwargs={'group_id': g.id}),
            user=g.owner.user,
            )
        twostep_response = client.get(
            reverse(
                'add_student', kwargs={'group_id': g.id}) + '?created=1',
            user=g.owner.user,
            )

        assert len(normal_response.html.findAll('ol', 'form-steps')) == 0
        assert len(twostep_response.html.findAll('ol', 'form-steps')) == 1


    def test_add_student(self, client):
        """User can add a student."""
        teacher = factories.ProfileFactory.create(school_staff=True)
        form = client.get(
            reverse('add_student'), user=teacher.user).forms['add-student-form']
        form['name'] = "Some Student"
        response = form.submit()

        student = teacher.students[0]

        assert response.status_code == 302, response.body
        assert response['Location'] == utils.location(
            reverse('village', kwargs={'student_id': student.id}))


    def test_add_student_in_group(self, client):
        """User can add a student in a group context."""
        group = factories.GroupFactory.create(owner__school_staff=True)
        form = client.get(
            reverse('add_student', kwargs={'group_id': group.id }),
            user=group.owner.user,
            ).forms['add-student-form']
        form['name'] = "Some Student"
        response = form.submit()

        student = group.students.get()

        assert response.status_code == 302, response.body
        assert response['Location'] == utils.location(
            reverse('village', kwargs={'student_id': student.id}),
            ) + "?group=" + str(group.id)


    def test_validation_error(self, client):
        """Name of student must be provided."""
        teacher = factories.ProfileFactory.create(school_staff=True)
        form = client.get(
            reverse('add_student'), user=teacher.user).forms['add-student-form']
        response = form.submit(status=200)

        response.mustcontain("field is required")


    def test_requires_school_staff(self, client):
        """Adding a student requires ``school_staff`` attribute."""
        someone = factories.ProfileFactory.create(school_staff=False)
        response = client.get(
            reverse('add_student'), user=someone.user, status=302).follow()

        response.mustcontain("don't have access"), response.html


    def test_anonymous_user_doesnt_blow_up(self, client):
        """Anonymous user on school-staff-required redirects gracefully."""
        response = client.get(reverse('add_student'), status=302).follow()

        assert "don't have access" in response.content



class TestEditStudent(GroupContextTests):
    """Tests for edit_student view."""
    def url(self, student=None):
        """Shortcut to get URL of edit-student view."""
        if student is None:
            student = factories.ProfileFactory.create()
        return reverse('edit_student', kwargs={'student_id': student.id})


    def test_edit_student(self, client):
        """User can edit a student."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        form = client.get(
            self.url(rel.student),
            user=rel.elder.user,
            ).forms['edit-student-form']
        form['name'] = "Some Student"
        response = form.submit(status=302)

        assert response['Location'] == utils.location(
            reverse('village', kwargs={'student_id': rel.student.id}))
        assert utils.refresh(rel.student).name == "Some Student"


    def test_remove_student(self, client):
        """User can remove a student."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True, to_profile__name="Some Student")
        form = client.get(
            self.url(rel.student),
            user=rel.elder.user,
            ).forms['edit-student-form']
        response = form.submit('remove', status=302)

        assert response['Location'] == utils.location(reverse('all_students'))
        response.follow().mustcontain("Student 'Some Student' removed.")
        assert utils.deleted(rel)


    def test_remove_student_in_group(self, client):
        """User can remove a student."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        group = factories.GroupFactory.create(owner=rel.elder)
        group.students.add(rel.student)

        form = client.get(
            self.url(rel.student) + '?group=%s' % group.id,
            user=rel.elder.user,
            ).forms['edit-student-form']
        response = form.submit('remove', status=302)

        assert response['Location'] == utils.location(
            reverse('group', kwargs={'group_id': group.id}))
        assert utils.deleted(rel)


    def test_maintain_group_context_on_redirect(self, client):
        """The group context is passed on through the form submission."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        group = factories.GroupFactory.create(owner=rel.elder)
        group.students.add(rel.student)

        form = client.get(
            self.url(rel.student) + '?group=%s' % group.id,
            user=rel.elder.user,
            ).forms['edit-student-form']
        form['name'] = "Some Student"
        response = form.submit().follow()

        assert response.context['group'] == group


    def test_validation_error(self, client):
        """Name of student must be provided."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        form = client.get(
            self.url(rel.student),
            user=rel.elder.user,
            ).forms['edit-student-form']
        form['name'] = ""
        response = form.submit(status=200)

        response.mustcontain("field is required")


    def test_requires_relationship(self, client):
        """Editing a student requires elder relationship."""
        someone = factories.ProfileFactory.create(school_staff=True)
        client.get(self.url(), user=someone.user, status=404)


    def test_requires_school_staff(self, client):
        """Editing a student requires ``school_staff`` attribute."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=False)
        response = client.get(
            self.url(rel.student), user=rel.elder.user, status=302).follow()

        response.mustcontain("don't have access"), response.html



class TestAddGroup(object):
    """Tests for add_group view."""
    def test_add_group(self, client):
        """User can add a group."""
        teacher = factories.ProfileFactory.create(school_staff=True)
        form = client.get(
            reverse('add_group'), user=teacher.user).forms['add-group-form']
        form['name'] = "Some Group"
        response = form.submit(status=302)

        group = teacher.owned_groups.get()

        assert group.name == "Some Group"
        assert response['Location'] == utils.location(
            reverse('add_student', kwargs={'group_id': group.id})
            + '?created=1'
            )


    def test_add_group_with_student(self, client):
        """User can add a group with a student."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        form = client.get(
            reverse('add_group'), user=rel.elder.user).forms['add-group-form']
        form['name'] = "Some Group"
        form['students'] = [str(rel.student.pk)]
        response = form.submit(status=302)

        group = rel.elder.owned_groups.get()

        assert set(group.students.all()) == {rel.student}
        assert response['Location'] == utils.location(
            reverse('group', kwargs={'group_id': group.id}))


    def test_validation_error(self, client):
        """Name of group must be provided."""
        teacher = factories.ProfileFactory.create(school_staff=True)
        form = client.get(
            reverse('add_group'), user=teacher.user).forms['add-group-form']
        response = form.submit(status=200)

        response.mustcontain("field is required")


    def test_requires_school_staff(self, client):
        """Adding a group requires ``school_staff`` attribute."""
        someone = factories.ProfileFactory.create(school_staff=False)
        response = client.get(
            reverse('add_group'), user=someone.user, status=302).follow()

        response.mustcontain("don't have access"), response.html



class TestEditGroup(object):
    """Tests for edit_group view."""
    def url(self, group=None):
        """Shortcut to get URL of edit-group view."""
        if group is None:
            group = factories.GroupFactory.create()
        return reverse('edit_group', kwargs={'group_id': group.id})


    def test_edit_group(self, client):
        """User can edit a group."""
        group = factories.GroupFactory.create(owner__school_staff=True)
        form = client.get(
            self.url(group),
            user=group.owner.user,
            ).forms['edit-group-form']
        form['name'] = "Some Group"
        response = form.submit(status=302)

        assert response['Location'] == utils.location(
            reverse('group', kwargs={'group_id': group.id}))
        assert utils.refresh(group).name == "Some Group"


    def test_remove_group(self, client):
        """User can remove a group."""
        group = factories.GroupFactory.create(
            owner__school_staff=True, name="Some Group")
        form = client.get(
            self.url(group),
            user=group.owner.user,
            ).forms['edit-group-form']
        response = form.submit('remove', status=302)

        response.follow().mustcontain("Group 'Some Group' removed.")
        assert utils.deleted(group)


    def test_validation_error(self, client):
        """Name of group must be provided."""
        group = factories.GroupFactory.create(
            owner__school_staff=True)
        form = client.get(
            self.url(group),
            user=group.owner.user,
            ).forms['edit-group-form']
        form['name'] = ""
        response = form.submit(status=200)

        response.mustcontain("field is required")


    def test_requires_owner(self, client):
        """Editing a group requires being its owner."""
        group = factories.GroupFactory.create(
            owner__school_staff=True)
        client.get(
            self.url(group),
            user=factories.ProfileFactory.create(school_staff=True).user,
            status=404,
            )



class TestInviteTeacher(GroupContextTests):
    """Tests for invite_teacher view."""
    def url(self, student):
        return reverse('invite_teacher', kwargs=dict(student_id=student.id))


    def test_invite_teacher(self, client):
        """User can invite a teacher."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        response = client.get(self.url(rel.student), user=rel.elder.user)
        form = response.forms['invite-teacher-form']
        form['email'] = "ms.johns@example.com"
        form['role'] = "Math Teacher"
        response = form.submit(status=302)

        assert response['Location'] == utils.location(
            reverse('village', kwargs={'student_id': rel.student.id}))

        # invite email is sent to new elder
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [u'ms.johns@example.com']

        # relationship with student is created
        assert rel.student.relationships_to.count() == 2


    def test_maintain_group_context_on_redirect(self, client):
        """The group context is passed on through the form submission."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        group = factories.GroupFactory.create(owner=rel.elder)
        group.students.add(rel.student)

        form = client.get(
            self.url(rel.student) + '?group=%s' % group.id,
            user=rel.elder.user,
            ).forms['invite-teacher-form']
        form['email'] = "ms.johns@example.com"
        form['role'] = "Father"
        response = form.submit().follow()

        assert response.context['group'] == group


    def test_validation_error(self, client):
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        response = client.get(self.url(rel.student), user=rel.elder.user)
        form = response.forms['invite-teacher-form']
        form['email'] = "ms.johns@example.com"
        form['role'] = ""
        response = form.submit(status=200)

        response.mustcontain("field is required")


    def test_requires_school_staff(self, client):
        """Inviting teachers requires ``school_staff`` attribute."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=False)
        response = client.get(
            self.url(rel.student), user=rel.elder.user, status=302).follow()

        response.mustcontain("don't have access"), response.html


    def test_ajax(self, client):
        """Can load the view via Ajax without error."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        client.get(self.url(rel.student), user=rel.elder.user, ajax=True)


    def test_unauthed_ajax(self, client):
        """An unauthenticated ajax request gets 403 not redirect."""
        rel = factories.RelationshipFactory.create()
        client.get(
            self.url(rel.student), user=rel.elder.user, ajax=True, status=403)


    def test_requires_relationship(self, client):
        """Only a teacher of that student can invite more."""
        elder = factories.ProfileFactory.create(school_staff=True)
        student = factories.ProfileFactory.create()

        client.get(self.url(student), user=elder.user, status=404)



class TestInviteTeacherToGroup(object):
    """Tests for invite_teacher_to_group view."""
    def url(self, group):
        return reverse('invite_teacher', kwargs=dict(group_id=group.id))


    def test_invite_teacher_to_group(self, client):
        """User can invite an teacher to a group."""
        group = factories.GroupFactory.create(owner__school_staff=True)
        response = client.get(self.url(group=group), user=group.owner.user)
        form = response.forms['invite-teacher-form']
        form['email'] = "ms.johns@example.com"
        form['role'] = "Math Teacher"
        response = form.submit(status=302)

        assert response['Location'] == utils.location(
            reverse('group', kwargs={'group_id': group.id}))

        # group membership is created
        assert group.elders.count() == 1


    def test_validation_error(self, client):
        group = factories.GroupFactory.create(owner__school_staff=True)
        response = client.get(self.url(group), user=group.owner.user)
        form = response.forms['invite-teacher-form']
        form['email'] = "ms.johns@example.com"
        form['role'] = ""
        response = form.submit(status=200)

        response.mustcontain("field is required")


    def test_requires_school_staff(self, client):
        """Inviting teachers requires ``school_staff`` attribute."""
        group = factories.GroupFactory.create(owner__school_staff=False)
        response = client.get(
            self.url(group), user=group.owner.user, status=302).follow()

        response.mustcontain("don't have access"), response.html


    def test_ajax(self, client):
        """Can load the view via Ajax without error."""
        group = factories.GroupFactory.create(owner__school_staff=True)
        client.get(self.url(group), user=group.owner.user, ajax=True)


    def test_unauthed_ajax(self, client):
        """An unauthenticated ajax request gets 403 not redirect."""
        group = factories.GroupFactory.create()
        client.get(
            self.url(group), user=group.owner.user, ajax=True, status=403)


    def test_requires_ownership(self, client):
        """Only owner of the group can invite more."""
        elder = factories.ProfileFactory.create(school_staff=True)
        group = factories.GroupFactory.create()

        client.get(self.url(group), user=elder.user, status=404)



class TestInviteFamily(GroupContextTests):
    """Tests for invite_family view."""
    def url(self, student):
        return reverse('invite_family', kwargs=dict(student_id=student.id))


    def test_invite_family(self, client):
        """User can invite a family member."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        response = client.get(self.url(rel.student), user=rel.elder.user)
        form = response.forms['invite-family-form']
        form['phone'] = "312-456-1234"
        form['role'] = "Father"
        with mock.patch('portfoliyo.tasks.send_sms.delay') as mock_send:
            response = form.submit(status=302)

        assert response['Location'] == utils.location(
            reverse('village', kwargs={'student_id': rel.student.id}))

        # invite sms is sent to new elder
        assert mock_send.call_count == 1
        assert mock_send.call_args[0][0] == '+13124561234'

        # relationship with student is created
        assert rel.student.relationships_to.count() == 2


    def test_prepopulate_phone(self, client):
        """Can prepopulate phone from query string."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        response = client.get(
            self.url(rel.student) + '?phone=321', user=rel.elder.user)
        form = response.forms['invite-family-form']

        assert form['phone'].value == '321'


    def test_maintain_group_context_on_redirect(self, client):
        """The group context is passed on through the form submission."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        group = factories.GroupFactory.create(owner=rel.elder)
        group.students.add(rel.student)

        form = client.get(
            self.url(rel.student) + '?group=%s' % group.id,
            user=rel.elder.user,
            ).forms['invite-family-form']
        form['phone'] = "312-456-1234"
        form['role'] = "Father"
        response = form.submit().follow()

        assert response.context['group'] == group


    def test_validation_error(self, client):
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        response = client.get(self.url(rel.student), user=rel.elder.user)
        form = response.forms['invite-family-form']
        form['phone'] = ""
        form['role'] = "mom"
        form['name'] = "Some Mom"
        response = form.submit(status=200)

        response.mustcontain(u"field is required")


    def test_requires_school_staff(self, client):
        """Inviting family requires ``school_staff`` attribute."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=False)
        response = client.get(
            self.url(rel.student), user=rel.elder.user, status=302).follow()

        response.mustcontain("don't have access"), response.html


    def test_unauthed_ajax(self, client):
        """An unauthenticated ajax request gets 403 not redirect."""
        rel = factories.RelationshipFactory.create()
        client.get(
            self.url(rel.student), user=rel.elder.user, ajax=True, status=403)


    def test_requires_relationship(self, client):
        """Only a teacher of that student can invite family."""
        elder = factories.ProfileFactory.create(school_staff=True)
        student = factories.ProfileFactory.create()

        client.get(self.url(student), user=elder.user, status=404)



class TestGetPosts(object):
    """Tests for _get_posts utility method."""
    def assert_posts(self, data, posts):
        """Given posts (only) are listed in given order in ``data``."""
        assert [p.id for p in posts] == [p['post_id'] for p in data['objects']]


    def test_student(self, db, redis):
        """Given student, returns posts in student village."""
        profile = factories.ProfileFactory.create()
        post1 = factories.PostFactory.create()
        post2 = factories.PostFactory.create(student=post1.student)

        # one for posts, one for attachments, one for post-count
        with utils.assert_num_queries(3):
            self.assert_posts(
                views._get_posts(profile, student=post1.student),
                [post1, post2],
                )


    def test_group(self, db):
        """Given group, returns posts in group."""
        post1 = factories.BulkPostFactory.create()
        post2 = factories.BulkPostFactory.create(group=post1.group)

        # one for posts, one for post-count
        with utils.assert_num_queries(2):
            self.assert_posts(
                views._get_posts(post1.group.owner, group=post1.group),
                [post1, post2],
                )


    def test_all_students_group(self, db):
        """Given all-students group, returns posts in group."""
        post1 = factories.BulkPostFactory.create(group=None)
        post2 = factories.BulkPostFactory.create(
            group=None, author=post1.author)

        with utils.assert_num_queries(2):
            self.assert_posts(
                views._get_posts(
                    post1.author, group=model.AllStudentsGroup(post1.author)),
                [post1, post2],
                )


    def test_neither(self, db):
        """Given neither, returns no posts."""
        profile = factories.ProfileFactory.create()

        self.assert_posts(views._get_posts(profile), [])


    def test_ordering(self, db, redis):
        """Posts are ordered by timestamp."""
        profile = factories.ProfileFactory.create()
        second_post = factories.PostFactory.create(
            timestamp=datetime.datetime(2013, 1, 25, 12))
        first_post = factories.PostFactory.create(
            student=second_post.student,
            timestamp=datetime.datetime(2013, 1, 25, 11),
            )

        self.assert_posts(
            views._get_posts(profile, student=first_post.student),
            [first_post, second_post],
            )


    def test_unread(self, db, redis):
        """Marks posts in student village correctly as read/unread."""
        profile = factories.ProfileFactory.create()
        read_post = factories.PostFactory.create()
        unread_post = factories.PostFactory.create(
            student=read_post.student)
        model.unread.mark_unread(unread_post, profile)

        expected = [(read_post.id, False), (unread_post.id, True)]
        data = views._get_posts(profile, student=read_post.student)
        found = [(p['post_id'], p['unread']) for p in data['objects']]

        assert expected == found


    def test_mine(self, db, redis):
        """Marks posts in student village correctly as mine/not."""
        profile = factories.ProfileFactory.create()
        my_post = factories.PostFactory.create(author=profile)
        other_post = factories.PostFactory.create(
            student=my_post.student)

        expected = [(my_post.id, True), (other_post.id, False)]
        data = views._get_posts(profile, student=my_post.student)
        found = [(p['post_id'], p['mine']) for p in data['objects']]

        assert expected == found


    def test_count(self, db, redis):
        """Return total post count too."""
        rel = factories.RelationshipFactory.create()
        for i in range(3):
            factories.PostFactory.create(student=rel.student)
        with mock.patch.object(views, 'BACKLOG_POSTS', 2):
            data = views._get_posts(rel.elder, student=rel.student)

        assert len(data['objects']) == 2
        assert data['meta']['total_count'] == 3
        assert data['meta']['limit'] == 2
        assert data['meta']['more'] == True



class TestVillage(GroupContextTests):
    """Tests for village chat view."""
    def url(self, student=None):
        if student is None:
            student = factories.ProfileFactory.create()
        return reverse('village', kwargs=dict(student_id=student.id))


    @pytest.mark.parametrize('link_target', ['invite_teacher', 'invite_family'])
    def test_link_only_if_staff(self, client, link_target):
        """Link with given target is only present for school staff."""
        parent_rel = factories.RelationshipFactory.create(
            from_profile__school_staff=False)
        teacher_rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True, to_profile=parent_rel.student)
        url = self.url(parent_rel.student)
        parent_response = client.get(url, user=parent_rel.elder.user)
        teacher_response = client.get(url, user=teacher_rel.elder.user)
        reverse_kwargs = {'student_id': parent_rel.student.id}
        target_url = reverse(link_target, kwargs=reverse_kwargs)
        parent_links = parent_response.html.findAll('a', href=target_url)
        teacher_links = teacher_response.html.findAll('a', href=target_url)

        assert len(teacher_links) == 1
        assert len(parent_links) == 0


    def test_requires_relationship(self, client):
        """Only an elder of that student can view village."""
        elder = factories.ProfileFactory.create(school_staff=True)
        student = factories.ProfileFactory.create()

        client.get(self.url(student), user=elder.user, status=404)


    def test_login_required_ajax(self, client):
        """An unauthenticated ajax request gets 403 not redirect."""
        client.get(self.url(), ajax=True, status=403)


    def test_superuser_readonly_view(self, client):
        """Superuser can get read-only view of other villages."""
        sup = factories.ProfileFactory.create(
            user__is_superuser=True)
        student = factories.ProfileFactory.create()

        client.get(self.url(student), user=sup.user)


    def test_marks_posts_read(self, client):
        """Loading the village marks all posts in village as read."""
        rel = factories.RelationshipFactory.create()
        post = factories.PostFactory.create(student=rel.student)
        post2 = factories.PostFactory.create(student=rel.student)
        unread.mark_unread(post, rel.elder)
        unread.mark_unread(post2, rel.elder)

        assert unread.is_unread(post, rel.elder)
        assert unread.is_unread(post2, rel.elder)

        client.get(self.url(rel.student), user=rel.elder.user)

        assert not unread.is_unread(post, rel.elder)
        assert not unread.is_unread(post2, rel.elder)


    def test_does_not_mark_posts_read_if_impersonating(self, client):
        """If impersonating, does not mark posts as read."""
        superuser = factories.ProfileFactory.create(
            user__is_superuser=True)
        rel = factories.RelationshipFactory.create(
            from_profile__user__email='foo@example.com')
        post = factories.PostFactory.create(student=rel.student)
        post2 = factories.PostFactory.create(student=rel.student)
        unread.mark_unread(post, rel.elder)
        unread.mark_unread(post2, rel.elder)

        assert unread.is_unread(post, rel.elder)
        assert unread.is_unread(post2, rel.elder)

        client.get(
            self.url(rel.student) + '?impersonate=foo@example.com',
            user=superuser.user,
            )

        assert unread.is_unread(post, rel.elder)
        assert unread.is_unread(post2, rel.elder)


    def test_posts(self, client):
        """Shows posts in village."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)

        # this post is in the village and should show up
        factories.PostFactory.create(
            author=rel.elder, student=rel.student, html_text="I am here.")
        # this is not in this village, and should not show up
        factories.PostFactory.create(
            author=rel.elder, html_text="I am not here.")

        response = client.get(
            self.url(rel.student), user=rel.elder.user, status=200)

        response.mustcontain("I am here.")
        assert "I am not here." not in response.content



class TestAllStudents(object):
    def url(self):
        return reverse('all_students')


    def test_all_students(self, client):
        """Shows all-students group posts."""
        teacher = factories.ProfileFactory.create(school_staff=True)
        group = factories.GroupFactory.create(owner=teacher)
        # this post is all-students and should show up
        factories.BulkPostFactory.create(
            author=teacher, group=None, html_text="I am here.")
        # this is not all-students, and should not.
        factories.BulkPostFactory.create(
            author=teacher, group=group, html_text="I am not here.")

        response = client.get(self.url(), user=teacher.user, status=200)

        response.mustcontain("I am here.")
        assert "I am not here." not in response.content



class TestGroupDetail(object):
    """Tests for group chat view."""
    def url(self, group=None):
        if group is None:
            group = factories.GroupFactory.create()
        return reverse('group', kwargs=dict(group_id=group.id))


    def test_group_detail(self, client):
        """Group detail page lists posts in group."""
        group = factories.GroupFactory.create(
            owner__school_staff=True)
        # this post is in the group and should show up
        factories.BulkPostFactory.create(
            author=group.owner, group=group, html_text="I am here.")
        # this is not in the group, and should not.
        factories.BulkPostFactory.create(
            author=group.owner, group=None, html_text="I am not here.")

        response = client.get(
            self.url(group), user=group.owner.user, status=200)

        response.mustcontain("I am here.")
        assert "I am not here." not in response.content


    def test_requires_ownership(self, client):
        """Only the owner of a group can view it."""
        group = factories.GroupFactory.create()
        someone = factories.ProfileFactory.create(
            school_staff=True, school=group.owner.school)

        client.get(self.url(group), user=someone.user, status=404)



class TestCreatePost(object):
    """Tests for create_post view."""
    def url(self, student=None, group=None):
        kwargs = {}
        if student is not None:
            kwargs['student_id'] = student.id
        elif group is not None:
            kwargs['group_id'] = group.id
        return reverse('create_post', kwargs=kwargs)


    def test_create_post(self, no_csrf_client):
        """Creates a post and returns its JSON representation."""
        rel = factories.RelationshipFactory.create()

        response = no_csrf_client.post(
            self.url(rel.student),
            {'text': 'foo'},
            user=rel.elder.user,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            )

        assert response.json['success']
        posts = response.json['objects']
        assert len(posts) == 1
        post = posts[0]
        assert post['text'] == 'foo'
        assert post['author_id'] == rel.elder.id
        assert post['student_id'] == rel.student.id
        assert post['mine']


    def test_requires_relationship(self, no_csrf_client):
        """Only an elder of that student can post."""
        elder = factories.ProfileFactory.create(school_staff=True)
        student = factories.ProfileFactory.create()

        no_csrf_client.post(
            self.url(student=student),
            {'text': 'foo'},
            user=elder.user,
            status=404,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            )


    def test_requires_group_owner(self, no_csrf_client):
        """Only the owner of a group can post to it."""
        elder = factories.ProfileFactory.create(school_staff=True)
        group = factories.GroupFactory.create()

        no_csrf_client.post(
            self.url(group=group),
            {'text': 'foo'},
            user=elder.user,
            status=404,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            )


    def test_requires_POST(self, client):
        """Cannot GET this URL."""
        client.get(self.url(), user=factories.UserFactory.create(), status=405)


    def test_requires_text(self, no_csrf_client):
        """Bad request error if no text given."""
        no_csrf_client.post(
            self.url(), {}, user=factories.UserFactory.create(), status=400)


    def test_create_post_with_smses(self, no_csrf_client):
        """Creates a post and sends SMSes."""
        rel = factories.RelationshipFactory.create(
            from_profile__name="Mr. Doe")
        other_rel = factories.RelationshipFactory.create(
            to_profile=rel.student,
            from_profile__phone='+13216540987',
            pyo_phone='+13336660000',
            from_profile__name='Recipient',
            from_profile__user__is_active=True,
            )

        target = 'portfoliyo.model.village.models.tasks.send_sms.delay'
        with mock.patch(target) as mock_send_sms:
            response = no_csrf_client.post(
                self.url(rel.student),
                {'text': 'foo', 'elder': [other_rel.elder.id]},
                user=rel.elder.user,
                headers={'X-Requested-With': 'XMLHttpRequest'},
                )

        post = response.json['objects'][0]
        assert post['sms_recipients'] == ['Recipient']
        mock_send_sms.assert_called_with(
            "+13216540987", "+13336660000", "foo --Mr. Doe")


    def test_create_meeting_with_present_and_extra_names(self, no_csrf_client):
        """Creates a meeting post with present profiles and extra names."""
        rel = factories.RelationshipFactory.create(
            from_profile__name="Mr. Doe")
        other_rel = factories.RelationshipFactory.create(
            to_profile=rel.student, from_profile__name='Mr. Ed')

        response = no_csrf_client.post(
            self.url(rel.student),
            {
                'text': 'foo',
                'type': 'meeting',
                'elder': other_rel.from_profile_id,
                'extra_name': ['Foo', 'Bar'],
                },
            user=rel.elder.user,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            )

        post = response.json['objects'][0]
        assert post['type']['is_meeting']
        assert post['present'] == ['Mr. Ed', 'Foo', 'Bar']
        assert not post['sms_recipients']


    def test_group_post_sms_all(self, no_csrf_client):
        """A group post automatically sends SMSes to all family members."""
        rel = factories.RelationshipFactory.create(
            from_profile__name="Mr. Doe")
        group = factories.GroupFactory.create(owner=rel.elder)
        group.students.add(rel.student)
        factories.RelationshipFactory.create(
            to_profile=rel.student,
            from_profile__phone='+13216540987',
            pyo_phone='+13336660000',
            from_profile__name='Recipient',
            from_profile__user__is_active=True,
            )

        target = 'portfoliyo.model.village.models.tasks.send_sms.delay'
        with mock.patch(target) as mock_send_sms:
            response = no_csrf_client.post(
                self.url(group=group),
                {'text': 'foo'},
                user=rel.elder.user,
                headers={'X-Requested-With': 'XMLHttpRequest'},
                )

        post = response.json['objects'][0]
        assert post['sms_recipients'] == ['Recipient']
        mock_send_sms.assert_called_with(
            "+13216540987", "+13336660000", "foo --Mr. Doe")


    def test_all_students_post_sms_all(self, no_csrf_client):
        """An all-students post sends SMSes to all family members."""
        rel = factories.RelationshipFactory.create(
            from_profile__name="Mr. Doe")
        factories.RelationshipFactory.create(
            to_profile=rel.student,
            from_profile__phone='+13216540987',
            pyo_phone='+13336660000',
            from_profile__name='Recipient',
            from_profile__user__is_active=True,
            )

        target = 'portfoliyo.model.village.models.tasks.send_sms.delay'
        with mock.patch(target) as mock_send_sms:
            response = no_csrf_client.post(
                self.url(),
                {'text': 'foo'},
                user=rel.elder.user,
                headers={'X-Requested-With': 'XMLHttpRequest'},
                )

        post = response.json['objects'][0]
        assert post['sms_recipients'] == ['Recipient']
        mock_send_sms.assert_called_with(
            "+13216540987", "+13336660000", "foo --Mr. Doe")


    def test_create_group_post(self, no_csrf_client):
        """Creates a group post and returns its JSON representation."""
        group = factories.GroupFactory.create()

        response = no_csrf_client.post(
            self.url(group=group),
            {'text': 'foo'},
            user=group.owner.user,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            )

        assert response.json['success']
        posts = response.json['objects']
        assert len(posts) == 1
        post = posts[0]
        assert post['text'] == 'foo'
        assert post['author_id'] == group.owner.id
        assert post['group_id'] == group.id


    def test_create_all_students_post(self, no_csrf_client):
        """Creates an all-students post and returns its JSON representation."""
        elder = factories.ProfileFactory.create()

        response = no_csrf_client.post(
            self.url(), {'text': 'foo'},
            user=elder.user,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            )

        assert response.json['success']
        posts = response.json['objects']
        assert len(posts) == 1
        post = posts[0]
        assert post['text'] == 'foo'
        assert post['author_id'] == elder.id
        assert post['group_id'] == 'all%s' % elder.id


    def test_create_post_with_sequence_id(self, no_csrf_client):
        """Can include a sequence_id with post, will get it back."""
        rel = factories.RelationshipFactory.create()

        response = no_csrf_client.post(
            self.url(rel.student),
            {'text': 'foo', 'author_sequence_id': '5'},
            user=rel.elder.user,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            )

        assert response.json['objects'][0]['author_sequence_id'] == '5'


    def test_length_limit(self, no_csrf_client):
        """Error if post is too long."""
        rel = factories.RelationshipFactory.create(
            from_profile__name='Fred')

        response = no_csrf_client.post(
            self.url(rel.student),
            {'text': 'f' * 160},
            user=rel.elder.user,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            status=400,
            )

        # length limit is 160 - len('Fred: ')
        assert response.json == {
            'success': False,
            'error': "Posts are limited to 153 characters."
            }


    def test_note_with_attachments(self, no_csrf_client):
        """Can create a note type post with attachments."""
        rel = factories.RelationshipFactory.create()

        response = no_csrf_client.post(
            self.url(rel.student),
            {'text': "Today I will fly!", 'type': 'note'},
            upload_files=[
                ('attachment', 'some1.txt', 'some1 text'),
                ('attachment', 'some2.txt', 'some2 text'),
                ],
            user=rel.elder.user,
            headers={'X-Requested-With': 'XMLHttpRequest'},
            )

        assert response.json['success']
        assert response.json['objects'][0]['type']['is_note']
        attachments = response.json['objects'][0]['attachments']
        attachment_filenames = set([a['name'] for a in attachments])
        assert attachment_filenames == {'some1.txt', 'some2.txt'}


    def test_note_no_ajax(self, client):
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)

        village_url = reverse(
            'village', kwargs={'student_id': rel.to_profile_id})

        form = client.get(
            village_url, user=rel.elder.user).forms['note-posting-form']

        form['text'] = "Today I will fly!"

        response = form.submit(status=302)

        assert response['Location'] == utils.location(village_url)
        assert model.Post.objects.get().original_text == "Today I will fly!"


    def test_maintain_group_context(self, client):
        """Can take ?group=id to maintain group nav context on redirect."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        group = factories.GroupFactory.create(owner=rel.elder)
        group.students.add(rel.student)

        village_url = reverse(
            'village',
            kwargs={'student_id': rel.to_profile_id},
            ) + "?group=%s" % group.id

        form = client.get(
            village_url, user=rel.elder.user).forms['note-posting-form']

        form['text'] = "Today I will fly!"

        response = form.submit(status=302)

        assert response['Location'] == utils.location(village_url)



class TestMarkPostRead(object):
    def url(self, post):
        """URL to mark given post read."""
        return reverse('mark_post_read', kwargs={'post_id': post.id})


    def test_mark_read(self, no_csrf_client):
        """Can mark a post read with POST to dedicated URI."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True)
        post = factories.PostFactory.create(student=rel.student)
        unread.mark_unread(post, rel.elder)

        no_csrf_client.post(
            self.url(post),
            user=rel.elder.user,
            status=200)

        assert not unread.is_unread(post, rel.elder)


    def test_does_not_mark_read_if_impersonating(self, no_csrf_client):
        """Does not mark the post read if user is impersonating another."""
        superuser = factories.ProfileFactory.create(
            user__is_superuser=True)
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True,
            from_profile__user__email='foo@example.com',
            )
        post = factories.PostFactory.create(student=rel.student)
        unread.mark_unread(post, rel.elder)

        no_csrf_client.post(
            self.url(post) + '?impersonate=foo@example.com',
            user=superuser.user,
            status=200,
            )

        assert unread.is_unread(post, rel.elder)



class TestEditFamily(object):
    def url(self, rel=None, elder=None, group=None):
        """rel is relationship between a student and elder to be edited."""
        assert elder or rel
        kwargs = {}
        if rel:
            kwargs['student_id'] = rel.student.id
            kwargs['elder_id'] = rel.elder.id
        elif elder:
            kwargs['elder_id'] = elder.id
        if group:
            kwargs['group_id'] = group.id
        return reverse('edit_elder', kwargs=kwargs)


    def test_success(self, client):
        """School staff can edit profile of non school staff."""
        rel = factories.RelationshipFactory(
            from_profile__name='Old Name', from_profile__role='Old Role')
        editor_rel = factories.RelationshipFactory(
            from_profile__school_staff=True, to_profile=rel.to_profile)
        url = self.url(rel)

        form = client.get(
            url, user=editor_rel.elder.user).forms['edit-elder-form']
        form['name'] = 'New Name'
        form['role'] = 'New Role'
        form['phone'] = '+13216540987'
        res = form.submit(status=302)

        assert res['Location'] == utils.location(
            reverse('village', kwargs={'student_id': rel.student.id}))
        elder = utils.refresh(rel.elder)
        assert elder.name == 'New Name'
        assert elder.role == 'New Role'
        assert elder.phone == '+13216540987'


    def test_remove(self, client):
        """User can remove a family member from a village."""
        rel = factories.RelationshipFactory.create(
            from_profile__school_staff=False)
        editor_rel = factories.RelationshipFactory.create(
            from_profile__school_staff=True, to_profile=rel.student)
        form = client.get(
            self.url(rel),
            user=editor_rel.elder.user,
            ).forms['edit-elder-form']
        response = form.submit('remove', status=302)

        assert response['Location'] == utils.location(
            reverse('village', kwargs={'student_id': rel.student.id}))
        assert utils.deleted(rel)


    def test_error(self, client):
        """Test form redisplay with errors."""
        rel = factories.RelationshipFactory()
        editor_rel = factories.RelationshipFactory(
            from_profile__school_staff=True, to_profile=rel.to_profile)
        url = self.url(rel)

        form = client.get(
            url, user=editor_rel.elder.user).forms['edit-elder-form']
        form['name'] = 'New Name'
        form['role'] = ''
        res = form.submit(status=200)

        res.mustcontain('field is required')


    def test_in_group(self, client):
        """Can edit an elder from a group context."""
        elder = factories.ProfileFactory.create()
        editor = factories.ProfileFactory.create(
            school_staff=True, school=elder.school)
        group = factories.GroupFactory.create(owner=editor)
        group.elders.add(elder)

        form = client.get(
            self.url(elder=elder, group=group),
            user=editor.user,
            ).forms['edit-elder-form']
        form['name'] = 'New Name'
        form['role'] = 'New Role'
        form['phone'] = '+13216540987'
        form.submit()

        elder = utils.refresh(elder)
        assert elder.name == 'New Name'
        assert elder.role == 'New Role'


    def test_in_all_students_group(self, client):
        """Can edit an elder from the all-students group."""
        elder = factories.ProfileFactory.create()
        editor = factories.ProfileFactory.create(
            school_staff=True, school=elder.school)

        form = client.get(
            self.url(elder=elder), user=editor.user).forms['edit-elder-form']
        form['name'] = 'New Name'
        form['role'] = 'New Role'
        form['phone'] = '+13216540987'
        form.submit()

        elder = utils.refresh(elder)
        assert elder.name == 'New Name'
        assert elder.role == 'New Role'


    def test_school_staff_required(self, client):
        """Only school staff can access."""
        rel = factories.RelationshipFactory(
            from_profile__name='Old Name', from_profile__role='Old Role')
        editor_rel = factories.RelationshipFactory(
            from_profile__school_staff=False, to_profile=rel.to_profile)
        url = self.url(rel)

        res = client.get(
            url, user=editor_rel.elder.user, status=302).follow()

        res.mustcontain("don't have access")


    def test_cannot_edit_school_staff(self, client):
        """Cannot edit other school staff."""
        rel = factories.RelationshipFactory(
            from_profile__school_staff=True)
        editor_rel = factories.RelationshipFactory(
            from_profile__school_staff=True, to_profile=rel.to_profile)
        url = self.url(rel)

        client.get(url, user=editor_rel.elder.user, status=404)


    def test_requires_relationship(self, client):
        """Editing user must have relationship with student."""
        rel = factories.RelationshipFactory()
        editor = factories.ProfileFactory(school_staff=True)
        url = self.url(rel)

        client.get(url, user=editor.user, status=404)



class TestPdfParentInstructions(object):
    def test_basic(self, client):
        """Smoke test that we get a PDF response back and nothing breaks."""
        elder = factories.ProfileFactory.create(
            school_staff=True, code='ABCDEF')
        url = reverse('pdf_parent_instructions', kwargs={'lang': 'es'})
        resp = client.get(url, user=elder.user, status=200)

        content_disposition = 'attachment; filename="Portfoliyo Spanish.pdf"'
        assert resp.headers['Content-Disposition'] == content_disposition
        assert resp.headers['Content-Type'] == 'application/pdf'


    def test_group(self, client):
        """Can get a PDF for a group code."""
        group = factories.GroupFactory.create(
            owner__school_staff=True, name='1st Period Math')
        url = reverse(
            'pdf_parent_instructions',
            kwargs={'lang': 'en', 'group_id': group.id},
            )
        resp = client.get(url, user=group.owner.user, status=200)

        content_disposition = (
            'attachment; filename="Portfoliyo English - 1st Period Math.pdf"')
        assert resp.headers['Content-Disposition'] == content_disposition
        assert resp.headers['Content-Type'] == 'application/pdf'


    def test_unicode_transliteration(self, client):
        """Non-ASCII chars in group names translitered to ASCII filename."""
        group = factories.GroupFactory.create(
            owner__school_staff=True, name=u'1st Period—Math')
        url = reverse(
            'pdf_parent_instructions',
            kwargs={'lang': 'en', 'group_id': group.id},
            )
        resp = client.get(url, user=group.owner.user, status=200)

        content_disposition = (
            'attachment; filename="Portfoliyo English - 1st Period--Math.pdf"')
        assert resp.headers['Content-Disposition'] == content_disposition


    def test_must_own_group(self, client):
        """Can't get a PDF for a group that isn't yours."""
        group = factories.GroupFactory.create()
        someone = factories.ProfileFactory(school_staff=True)
        url = reverse(
            'pdf_parent_instructions',
            kwargs={'lang': 'en', 'group_id': group.id},
            )
        client.get(url, user=someone.user, status=404)


    def test_no_code(self, client):
        """Doesn't blow up if requesting user has no code."""
        elder = factories.ProfileFactory.create(school_staff=True)
        url = reverse('pdf_parent_instructions', kwargs={'lang': 'en'})
        resp = client.get(url, user=elder.user, status=200)

        content_disposition = 'attachment; filename="Portfoliyo English.pdf"'
        assert resp.headers['Content-Disposition'] == content_disposition
        assert resp.headers['Content-Type'] == 'application/pdf'
