import pickle
import os
import unittest
from kurt import kurt

SELF_PATH = os.path.dirname(os.path.abspath(__file__))


class TestPickle(unittest.TestCase):

    # TODO: Tests break with the default protocol

    def test_base_project(self):
        proj = kurt.Project()
        pickle.loads(pickle.dumps(proj, pickle.HIGHEST_PROTOCOL))

    def test_file(self):
        test_file = os.path.join(SELF_PATH, 'game.sb')
        proj = kurt.Project.load(test_file)
        pickle.loads(pickle.dumps(proj, pickle.HIGHEST_PROTOCOL))

    def test_pickle_image(self):
        original = kurt.Image.new((32, 32), (255, 0, 0))
        restored = pickle.loads(pickle.dumps(original))
        self.assertEqual(original._pil_image.mode, restored._pil_image.mode)
        self.assertEqual(original._pil_image.size, restored._pil_image.size)
        self.assertEqual(original._pil_image.tobytes(),
                         restored._pil_image.tobytes())
