# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models


def process_post(post):
    if 'sms' not in post.meta:
        meta_sms = []
        seen_ids = set()
        for highlight in post.meta.get('highlights', []):
            if highlight['sms_sent'] and (highlight['id'] not in seen_ids):
                meta_sms.append(
                    {
                        'id': highlight['id'],
                        'name': highlight['name'],
                        'role': highlight['role'],
                        'phone': highlight['phone'],
                        }
                    )
                seen_ids.add(highlight['id'])
        post.meta['sms'] = meta_sms
        post.save()



class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        for post in orm.Post.objects.all():
            process_post(post)
        for post in orm.BulkPost.objects.all():
            process_post(post)


    def backwards(self, orm):
        "Write your backwards methods here."

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '255', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'users.group': {
            'Meta': {'object_name': 'Group'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'elders': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'elder_in_groups'", 'blank': 'True', 'to': "orm['users.Profile']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'owned_groups'", 'to': "orm['users.Profile']"}),
            'students': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'student_in_groups'", 'blank': 'True', 'to': "orm['users.Profile']"})
        },
        'users.profile': {
            'Meta': {'object_name': 'Profile'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '20', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'declined': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email_notifications': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invited_by': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.Profile']", 'null': 'True', 'blank': 'True'}),
            'invited_in_group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.Group']", 'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '20', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'school': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.School']"}),
            'school_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'done'", 'max_length': '20'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        },
        'users.school': {
            'Meta': {'unique_together': "[('name', 'postcode')]", 'object_name': 'School'},
            'auto': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'postcode': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        'village.bulkpost': {
            'Meta': {'object_name': 'BulkPost'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'authored_bulkposts'", 'null': 'True', 'to': "orm['users.Profile']"}),
            'from_sms': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'bulk_posts'", 'null': 'True', 'to': "orm['users.Group']"}),
            'html_text': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'original_text': ('django.db.models.fields.TextField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 10, 18, 0, 0)'}),
            'to_sms': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'village.post': {
            'Meta': {'object_name': 'Post'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'authored_posts'", 'null': 'True', 'to': "orm['users.Profile']"}),
            'from_bulk': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'triggered'", 'null': 'True', 'to': "orm['village.BulkPost']"}),
            'from_sms': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'html_text': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meta': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'original_text': ('django.db.models.fields.TextField', [], {}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts_in_village'", 'to': "orm['users.Profile']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 10, 18, 0, 0)'}),
            'to_sms': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        }
    }

    complete_apps = ['village']
    symmetrical = True