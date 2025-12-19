import importlib
import os
import tempfile
import unittest


class ProgressModelsTest(unittest.TestCase):
    def test_progress_schema_and_apis(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ['HOME'] = td
            import database
            import models

            importlib.reload(database)
            importlib.reload(models)

            models.create_admin_if_absent()
            models.create_user('u_progress', 'pw', role='user', active=1, full_name='U')
            user = next(u for u in models.list_users() if u[1] == 'u_progress')
            user_id = int(user[0])

            module_id = models.upsert_progress_module('模块A')
            t1 = models.upsert_progress_task(module_id, '任务1', '描述1', 1)
            t2 = models.upsert_progress_task(module_id, '任务2', '描述2', 2)

            models.set_user_task_progress(user_id, t1, models.PROGRESS_STATUS_IN_PROGRESS, updated_by='admin:1')
            models.set_user_task_progress(user_id, t2, models.PROGRESS_STATUS_COMPLETED, updated_by='admin:1')

            mp = models.get_user_task_progress_map(user_id)
            self.assertEqual(mp[t1]['status'], models.PROGRESS_STATUS_IN_PROGRESS)
            self.assertEqual(mp[t2]['status'], models.PROGRESS_STATUS_COMPLETED)

            tree = models.get_user_progress_tree(user_id)
            self.assertEqual(len(tree), 1)
            self.assertEqual(tree[0]['module_id'], module_id)
            self.assertEqual([t['task_id'] for t in tree[0]['tasks']], [t1, t2])
            self.assertEqual(tree[0]['tasks'][0]['status'], models.PROGRESS_STATUS_IN_PROGRESS)
            self.assertEqual(tree[0]['tasks'][1]['status'], models.PROGRESS_STATUS_COMPLETED)

            models.delete_progress_module(module_id)


if __name__ == '__main__':
    unittest.main()

