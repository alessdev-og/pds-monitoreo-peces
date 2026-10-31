"""Comprobaciones numéricas independientes de los datos reales."""

import unittest
import numpy as np

from src.annotations import Observation, continuous_segments
from src.signals import amplitude_spectrum, moving_average, motion_metrics, uniform_resample


class SignalTests(unittest.TestCase):
    def test_fir_ramp_preserves_center_and_no_zero_padding(self):
        ramp = np.column_stack([np.arange(10.), np.ones(10)*7])
        filtered = moving_average(ramp)
        np.testing.assert_allclose(filtered[:, 0], np.arange(2., 8.))
        np.testing.assert_allclose(filtered[:, 1], 7)

    def test_irregular_time_interpolation_of_linear_motion(self):
        times = np.array([0, .04, .12, .16, .20, .24, .32, .40, .48, .56])
        grid, xy = uniform_resample(times, np.column_stack([10*times, -5*times]), 20)
        np.testing.assert_allclose(xy[:, 0], 10*grid)
        np.testing.assert_allclose(xy[:, 1], -5*grid)
        metrics = motion_metrics(xy, 20)
        self.assertAlmostEqual(metrics['mean_speed_px_s'], np.sqrt(125))

    def test_repeated_timestamps_rejected(self):
        with self.assertRaises(ValueError):
            uniform_resample([0, 1, 1, 2, 3], np.ones((5, 2)), 20)

    def test_fft_recovers_known_sinusoid(self):
        fs, samples, frequency, amplitude = 20, 400, 2, 3
        t = np.arange(samples)/fs
        f, a = amplitude_spectrum(amplitude*np.sin(2*np.pi*frequency*t) + 4*t, fs)
        i = 1 + np.argmax(a[1:])
        self.assertAlmostEqual(f[i], frequency)
        self.assertAlmostEqual(a[i], amplitude, places=2)

    def test_outside_gap_is_not_bridged(self):
        observations = [Observation(1, 'Fish', i, 1, 1, 2, 2, 0, 1) for i in [0, 1, 4, 5]]
        self.assertEqual([[o.frame for o in s] for s in continuous_segments(observations)], [[0, 1], [4, 5]])


if __name__ == '__main__':
    unittest.main()
