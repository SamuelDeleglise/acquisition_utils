"""
This is the general tests that verify the front-end implementation.
So there is not tests on internal logic of the code. It's just a
verification of the api. So as soon as saving and opening works,
everything is good.
"""

import os
import shutil

import unittest
import numpy as np

from quanalys.acquisition_utils import AcquisitionLoop, AcquisitionManager, AnalysisManager

TEST_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(TEST_DIR, "tmp_test_data")


class BasicTest(unittest.TestCase):
    """Test of saving simple data."""

    def setUp(self):
        AcquisitionManager.data_directory = DATA_DIR
        return super().setUpClass()

    def test_simple_save(self):
        """Save and load the simplest list."""
        x = np.linspace(0, 20*np.pi, 101)
        y = np.sin(x)
        AcquisitionManager.save_acquisition(x=x, y=y)

        fullpath = AcquisitionManager.get_ongoing_acquisition().fullpath
        AnalysisManager(fullpath, "")

        data = AnalysisManager.current_analysis

        assert data is not None

        self.assertTrue(np.all(x == data.get('x')))
        self.assertTrue(np.all(y == data.get('y')))

    def test_open_old_file(self):
        old_file_path = "tests/data/old_data_example.h5"
        data = AnalysisManager(old_file_path).current_analysis
        assert data, "File probably exists, but create analysisData object"
        self.assertAlmostEqual(
            np.abs(data.get('x') - (x := np.linspace(0, 10*np.pi, 101))).sum(), 0)
        self.assertAlmostEqual(
            np.abs(data.get('y') - np.sin(x)).sum(), 0)

    @classmethod
    def tearDownClass(cls):
        """Remove tmp_test_data directory ones all test finished."""
        data_directory = os.path.join(os.path.dirname(__file__), DATA_DIR)
        if os.path.exists(data_directory):
            shutil.rmtree(data_directory)
        return super().tearDownClass()


class LoopTest(unittest.TestCase):
    """Test of saving simple data."""

    @staticmethod
    def acquire_sine(freq, points):
        x = np.linspace(0, 10*np.pi, points)
        y = np.sin(freq*2*np.pi*x)
        return x, y

    @classmethod
    def setUpClass(cls) -> None:
        """This setUp method runs ones of LoopTest.
        It creates a dictionary to verify with."""
        AcquisitionManager.data_directory = DATA_DIR

        cls.points = 101
        cls.freqs = np.linspace(0, 0.4, 10)

        cls.data = {"freq": [], "y": []}
        for freq in cls.freqs:
            x, y = cls.acquire_sine(freq, cls.points)
            cls.data['y'].append(y)
            cls.data['freq'].append(freq)
        cls.data['x'] = x  # type: ignore

        return super().setUpClass()

    def test_classical_loop(self):
        """Save and load the simplest list.

        Protocol:

        for freq in freqs:
            x, y = ...
            push_to_save(y, freq)
        push_to_save(x)
        save()

        """
        # Protocol
        loop = AcquisitionLoop()
        for freq in loop(self.freqs):
            x, y = self.acquire_sine(freq, self.points)
            loop.append_data(y=y, freq=freq)
        loop.append_data(x=x)  # type: ignore
        AcquisitionManager.save_acquisition(loop_freq=loop)

        # Verification
        self.data_verification_for_simple_loop()

    def test_classical_loop_with_level(self):
        """Save and load the same list as the previous one,
        but we put push_to_save(x) inside loop with parameter level=-1,
        so it should give as the same result.

        Protocol:

        for freq in freqs:
            x, y = ...
            push_to_save(y, freq)
            push_to_save(x, level=-1)
        save()

        """
        # Protocol
        loop = AcquisitionLoop()
        for freq in loop(self.freqs):
            x, y = self.acquire_sine(freq, self.points)
            loop.append_data(y=y, freq=freq)
            loop.append_data(x=x, level=-1)
        AcquisitionManager.save_acquisition(loop_freq=loop)

        # Verification
        self.data_verification_for_simple_loop()

    def test_classical_loop_multisave(self):
        """Save and load the same list as previous one,
        but now we save on every iteration of cycle.

        Protocol:

        for freq in freqs:
            x, y = ...
            push_to_save(y, freq)
            push_to_save(x, level=-1)
            save()

        """
        # Protocol
        loop = AcquisitionLoop()
        for freq in loop(self.freqs):
            x, y = self.acquire_sine(freq, self.points)
            loop.append_data(y=y, freq=freq)
            loop.append_data(x=x, level=-1)
            AcquisitionManager.save_acquisition(loop_freq=loop)

        # Verification
        self.data_verification_for_simple_loop()

    def data_verification_for_simple_loop(self):
        fullpath = AcquisitionManager.get_ongoing_acquisition().fullpath
        AnalysisManager(fullpath)

        data = AnalysisManager.current_analysis
        assert data is not None

        loop_freq = data.get("loop_freq")
        assert loop_freq is not None, "Cannot get LoopData from saved data."

        for i, d in enumerate(loop_freq):
            self.assertAlmostEqual(self.data['freq'][i], d.freq)
            self.assertAlmostEqual(compare_np_array(self.data['y'][i], d.y), 0)
            self.assertAlmostEqual(compare_np_array(self.data['x'], d.x), 0)  # type: ignore

    @classmethod
    def tearDownClass(cls):
        """Remove tmp_test_data directory ones all test finished."""
        data_directory = os.path.join(os.path.dirname(__file__), DATA_DIR)
        if os.path.exists(data_directory):
            shutil.rmtree(data_directory)
        return super().tearDownClass()


class MultiLoopTest(unittest.TestCase):
    """Test of saving simple data."""

    @staticmethod
    def acquire_sine(freq, points, tau):
        x = np.linspace(10*tau, 10*tau+10*np.pi, points)
        y = np.sin(freq*2*np.pi*x)
        y *= np.exp(-x*tau)
        return x, y

    @classmethod
    def setUpClass(cls) -> None:
        """This setUp method runs ones of LoopTest.
        It creates a dictionary to verify with."""
        AcquisitionManager.data_directory = DATA_DIR

        cls.points = 101
        cls.freqs = np.linspace(0, 0.4, 10)
        cls.taus = np.linspace(0, 0.3, 5)

        cls.data = {"tau": [], "freq": [], "x": [], "y": []}
        for tau in cls.taus:
            cls.data['tau'].append(tau)
            cls.data['y'].append([])
            cls.data['freq'].append([])
            
            for freq in cls.freqs:
                x, y = cls.acquire_sine(freq, cls.points, tau)
                cls.data['y'][-1].append(y)
                cls.data['freq'][-1].append(freq)
            cls.data['x'].append(x)  # type: ignore

        return super().setUpClass()

    def test_classical_loop(self):
        """Save and load the simplest list.

        Protocol:

        for freq in freqs:
            x, y = ...
            push_to_save(y, freq)
        push_to_save(x)
        save()

        """
        # Protocol
        loop = AcquisitionLoop()

        for tau in loop(self.taus):
            loop.append_data(tau=tau)
            for freq in loop(self.freqs):
                x, y = self.acquire_sine(freq, self.points, tau)
                loop.append_data(y=y, freq=freq)
            loop.append_data(x=x)  # type: ignore
            
            AcquisitionManager.save_acquisition(loop_tau_freq=loop)

        # Verification
        self.data_verification_for_2d_loop()

    def data_verification_for_2d_loop(self):
        fullpath = AcquisitionManager.get_ongoing_acquisition().fullpath
        AnalysisManager(fullpath)

        data = AnalysisManager.current_analysis
        assert data is not None

        loop_freq = data.get("loop_tau_freq")
        assert loop_freq is not None, "Cannot get LoopData from saved data."

        for i, d in enumerate(loop_freq):
            for j, dd in enumerate(d):
                self.assertAlmostEqual(self.data['tau'][i], dd.tau)
                self.assertAlmostEqual(self.data['freq'][i][j], dd.freq)
                self.assertAlmostEqual(compare_np_array(self.data['y'][i][j], dd.y), 0)
                self.assertAlmostEqual(compare_np_array(self.data['x'][i], dd.x), 0)  # type: ignore

    @classmethod
    def tearDownClass(cls):
        """Remove tmp_test_data directory ones all test finished."""
        data_directory = os.path.join(os.path.dirname(__file__), DATA_DIR)
        if os.path.exists(data_directory):
            shutil.rmtree(data_directory)
        return super().tearDownClass()


def compare_np_array(array1: np.ndarray, array2: np.ndarray):
    return np.abs(array1 - array2).sum()  # type: ignore


if __name__ == '__main__':
    unittest.main()