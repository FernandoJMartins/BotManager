import unittest
from src.services.client_service import ClientService

class TestClientService(unittest.TestCase):
    
    def setUp(self):
        self.client_service = ClientService()
        self.test_client_id = "test_client_1"
    
    def test_add_client(self):
        result = self.client_service.add_client(self.test_client_id)
        self.assertTrue(result)
        self.assertIn(self.test_client_id, self.client_service.clients)

    def test_remove_client(self):
        self.client_service.add_client(self.test_client_id)
        result = self.client_service.remove_client(self.test_client_id)
        self.assertTrue(result)
        self.assertNotIn(self.test_client_id, self.client_service.clients)

    def test_get_client_info(self):
        self.client_service.add_client(self.test_client_id)
        client_info = self.client_service.get_client_info(self.test_client_id)
        self.assertEqual(client_info['client_id'], self.test_client_id)

    def test_remove_nonexistent_client(self):
        result = self.client_service.remove_client("nonexistent_client")
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()