import json
import unittest

from monolith.app import create_test_app

class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = create_test_app()
        self.client = self.app.test_client()
        self._ctx = self.app.test_request_context()
        self._ctx.push()

    def test_unauthorised_access(self):
        reply = self.client.post('/api/message/draft', data=dict(text=""))
        assert reply.status_code == 401

    def test_empty_draft(self): 
        with self.client:
            reply = self.client.post('/login', data=dict(
                email="example@example.com",
                password="admin"
            ), follow_redirects=True)

            reply = self.client.post('/api/message/draft', data=dict(text=""))
            assert reply.status_code == 400


    def test_draft_insert_delete(self):
        with self.client:
            reply = self.client.post('/login', data=dict(
                email="example@example.com",
                password="admin"
            ), follow_redirects=True)

            reply = self.client.get('/api/message/user_drafts')
            assert reply.status_code == 200

            reply = self.client.post('/api/message/draft', data=dict(text="Lorem ipsum dolor..."))
            data = reply.get_json()
            assert reply.status_code == 200
            assert data['message_id'] == 1

            reply = self.client.get('/api/message/user_drafts')
            data = reply.get_json()
            assert reply.status_code == 200
            assert data[0]['text'] == "Lorem ipsum dolor..."
        
            reply = self.client.delete('/api/message/draft', data=dict(message_id=1))
            data = reply.get_json()
            assert reply.status_code == 200
            assert int(data['message_id']) == 1
