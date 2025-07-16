from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from pytils.translit import slugify


from notes.forms import WARNING
from notes.models import Note


User = get_user_model()


class TestNoteCreation(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('notes:add')
        cls.author = User.objects.create(username='author')
        cls.form_data = {
            'title': 'Заголовок',
            'text': 'Текст',
            'slug': 'slug',
            'author': cls.author
        }

    def test_not_create_note_of_anonymous_user(self):
        response = self.client.post(self.url, data=self.form_data)
        login_url = reverse('users:login')
        expected_url = f'{login_url}?next={self.url}'
        self.assertRedirects(response, expected_url)
        notes_count = Note.objects.count()
        self.assertEqual(notes_count, 0)

    def test_create_note_of_authorized_user(self):
        self.client.force_login(self.author)
        response = self.client.post(self.url, data=self.form_data)
        self.assertRedirects(response, '/done/')
        notes_count = Note.objects.count()
        self.assertEqual(notes_count, 1)
        note = Note.objects.get()
        self.assertEqual(note.text, self.form_data['text'])
        self.assertAlmostEqual(note.author, self.author)

    def test_empty_slug(self):
        self.form_data.pop('slug')
        self.client.force_login(self.author)
        response = self.client.post(self.url, data=self.form_data)
        self.assertRedirects(response, reverse('notes:success'))
        self.assertEqual(Note.objects.count(), 1)
        new_note = Note.objects.get()
        expected_slug = slugify(self.form_data['title'])
        self.assertEqual(new_note.slug, expected_slug)


class TestSlug(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('notes:add')
        cls.author = User.objects.create(username='author')
        cls.note = Note.objects.create(
            title='Заголовок',
            text='Текст',
            slug='slug',
            author=cls.author
        )
        cls.form_data = {
            'title': 'Другой заголовок',
            'text': 'Другой текст',
            'slug': 'new_slug',
            'author': cls.author
        }

    def test_not_unique_slug(self):
        self.form_data['slug'] = self.note.slug
        self.client.force_login(self.author)
        response = self.client.post(self.url, data=self.form_data)
        self.assertFormError(
            form=response.context['form'],
            field='slug',
            errors=f'{self.note.slug}{WARNING}'
        )
        self.assertEqual(Note.objects.count(), 1)


class TestDeleteEditNote(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username='new_author')
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)
        cls.reader = User.objects.create(username='reader')
        cls.reader_client = Client()
        cls.reader_client.force_login(cls.reader)
        cls.note = Note.objects.create(
            title='Заголовок',
            text='Текст',
            slug='slug',
            author=cls.author
        )
        cls.note_url = reverse('notes:detail', args=(cls.note.slug,))
        cls.success_url = reverse('notes:success')
        cls.edit_url = reverse('notes:edit', args=(cls.note.slug,))
        cls.delete_url = reverse('notes:delete', args=(cls.note.slug,))

        cls.form_data = {
            'title': 'Другой заголовок',
            'text': 'Другой текст',
            'slug': 'new_slug',
            'author': cls.author
        }

    def test_edit_note_of_author(self):
        response = self.author_client.post(self.edit_url, data=self.form_data)
        self.assertRedirects(response, self.success_url)
        self.note.refresh_from_db()
        self.assertEqual(self.note.text, self.form_data['text'])

    def test_delete_note_of_author(self):
        response = self.author_client.delete(self.delete_url)
        self.assertRedirects(response, self.success_url)
        notes_count = Note.objects.count()
        self.assertEqual(notes_count, 0)

    def test_not_edit_note_reader(self):
        response = self.reader_client.post(self.edit_url, data=self.form_data)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.note.refresh_from_db()
        self.assertEqual(self.note.text, 'Текст')

    def test_not_delete_note_reader(self):
        response = self.reader_client.delete(self.delete_url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        notes_count = Note.objects.count()
        self.assertEqual(notes_count, 1)
