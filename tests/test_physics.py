"""Tests portados 1:1 desde `C:\\Mis_proyectos\\Proyecto\\optic_simulator\\tests\\test_physics.py`.

Solo se cambió el import (`physics_engine` → `electro_sim.physics_engine.fresnel`,
`dispersion_models` → `electro_sim.physics_engine.dispersion`). Los nombres de las
clases y métodos, los valores esperados y las tolerancias se preservan
idénticos para mantener equivalencia numérica estricta con el motor origen.
Pytest ejecuta `unittest.TestCase` de forma nativa.
"""

import unittest
import numpy as np

from electro_sim.physics_engine.fresnel import FresnelEngine
from electro_sim.physics_engine.dispersion import (
    DispersionModel,
    ConstantModel,
    SellmeierModel,
    CauchyModel,
    DrudeModel,
    DrudeLorentzModel,
    MATERIAL_PRESETS,
)


class TestFresnelEngine(unittest.TestCase):

    def test_air_glass_normal_incidence(self):
        engine = FresnelEngine(1.0, 1.0, 1.5**2, 1.0)
        engine = FresnelEngine(1.0, 1.0, 2.25, 1.0)

        res = engine.calculate_coefficients(0)

        self.assertAlmostEqual(res['TE']['R'], 0.04, places=4)
        self.assertAlmostEqual(res['TM']['R'], 0.04, places=4)
        self.assertAlmostEqual(res['TE']['T'], 0.96, places=4)

    def test_brewster_angle(self):
        engine = FresnelEngine(1.0, 1.0, 2.25, 1.0)
        theta_b = engine.get_brewster_angle()
        self.assertAlmostEqual(theta_b, 56.3099, places=3)

        res = engine.calculate_coefficients(theta_b)
        self.assertAlmostEqual(res['TM']['R'], 0.0, places=5)

    def test_tir(self):
        engine = FresnelEngine(2.25, 1.0, 1.0, 1.0)
        theta_c = engine.get_critical_angle()
        self.assertAlmostEqual(theta_c, 41.8103, places=3)

        res_below = engine.calculate_coefficients(30)
        self.assertTrue(res_below['TE']['T'] > 0)

        res_above = engine.calculate_coefficients(60)
        self.assertAlmostEqual(res_above['TE']['R'], 1.0, places=4)
        self.assertAlmostEqual(res_above['TM']['R'], 1.0, places=4)
        self.assertAlmostEqual(res_above['TE']['T'], 0.0, places=4)

    def test_magnetic_material(self):
        engine = FresnelEngine(4.0, 1.0, 1.0, 4.0)
        res = engine.calculate_coefficients(0)

        self.assertEqual(engine.n1, 2.0)
        self.assertEqual(engine.n2, 2.0)

        self.assertAlmostEqual(res['TE']['R'], 0.36, places=4)


class TestReflectanceTransmittance(unittest.TestCase):

    def _air_glass(self):
        return FresnelEngine(1.0, 1.0, 2.25, 1.0)

    def _glass_air(self):
        return FresnelEngine(2.25, 1.0, 1.0, 1.0)

    def _magnetic(self):
        return FresnelEngine(4.0, 1.0, 1.0, 4.0)

    def test_energy_conservation_te_air_glass(self):
        engine = self._air_glass()
        for angle in np.linspace(0, 80, 10):
            res = engine.calculate_coefficients(angle)
            total = res['TE']['R'] + res['TE']['T']
            self.assertAlmostEqual(total, 1.0, places=5)

    def test_energy_conservation_tm_air_glass(self):
        engine = self._air_glass()
        for angle in np.linspace(0, 80, 10):
            res = engine.calculate_coefficients(angle)
            total = res['TM']['R'] + res['TM']['T']
            self.assertAlmostEqual(total, 1.0, places=5)

    def test_energy_conservation_te_glass_air(self):
        engine = self._glass_air()
        for angle in np.linspace(0, 40, 8):
            res = engine.calculate_coefficients(angle)
            total = res['TE']['R'] + res['TE']['T']
            self.assertAlmostEqual(total, 1.0, places=5)

    def test_energy_conservation_magnetic(self):
        engine = self._magnetic()
        for angle in np.linspace(0, 80, 8):
            res_te = engine.calculate_coefficients(angle)['TE']
            res_tm = engine.calculate_coefficients(angle)['TM']
            self.assertAlmostEqual(res_te['R'] + res_te['T'], 1.0, places=5)
            self.assertAlmostEqual(res_tm['R'] + res_tm['T'], 1.0, places=5)

    def test_normal_incidence_r_t_values(self):
        engine = self._air_glass()
        res = engine.calculate_coefficients(0)
        self.assertAlmostEqual(res['TE']['R'], 0.04, places=5)
        self.assertAlmostEqual(res['TE']['T'], 0.96, places=5)
        self.assertAlmostEqual(res['TM']['R'], 0.04, places=5)
        self.assertAlmostEqual(res['TM']['T'], 0.96, places=5)

    def test_grazing_incidence_full_reflection(self):
        engine = self._air_glass()
        res = engine.calculate_coefficients(89.9)
        self.assertGreater(res['TE']['R'], 0.98)
        self.assertGreater(res['TM']['R'], 0.98)
        self.assertLess(res['TE']['T'], 0.02)
        self.assertLess(res['TM']['T'], 0.02)

    def test_brewster_zero_r_full_t_tm(self):
        engine = self._air_glass()
        theta_b = engine.get_brewster_angle()
        res = engine.calculate_coefficients(theta_b)
        self.assertAlmostEqual(res['TM']['R'], 0.0, places=5)
        self.assertAlmostEqual(res['TM']['T'], 1.0, places=5)

    def test_magnetic_normal_incidence_r_0p36(self):
        engine = self._magnetic()
        res = engine.calculate_coefficients(0)
        self.assertAlmostEqual(res['TE']['R'], 0.36, places=4)
        self.assertAlmostEqual(res['TM']['R'], 0.36, places=4)
        self.assertAlmostEqual(res['TE']['T'], 0.64, places=4)
        self.assertAlmostEqual(res['TM']['T'], 0.64, places=4)

    def test_tir_full_reflection_above_critical(self):
        engine = self._glass_air()
        theta_c = engine.get_critical_angle()
        for delta in (5, 15):
            angle = theta_c + delta
            res = engine.calculate_coefficients(angle)
            self.assertAlmostEqual(res['TE']['R'], 1.0, places=4)
            self.assertAlmostEqual(res['TM']['R'], 1.0, places=4)
            self.assertAlmostEqual(res['TE']['T'], 0.0, places=4)
            self.assertAlmostEqual(res['TM']['T'], 0.0, places=4)

    def test_tir_transmission_below_critical(self):
        engine = self._glass_air()
        theta_c = engine.get_critical_angle()
        for angle in (5, 15, 25, 35):
            if angle < theta_c:
                res = engine.calculate_coefficients(angle)
                self.assertGreater(res['TE']['T'], 0)
                self.assertLess(res['TE']['R'], 1.0)

    def test_symmetric_interface_zero_reflection(self):
        engine = FresnelEngine(2.0, 1.0, 2.0, 1.0)
        for angle in np.linspace(0, 80, 9):
            res = engine.calculate_coefficients(angle)
            self.assertAlmostEqual(res['TE']['R'], 0.0, places=5)
            self.assertAlmostEqual(res['TM']['R'], 0.0, places=5)
            self.assertAlmostEqual(res['TE']['T'], 1.0, places=5)

    def test_r_t_range_always_between_0_and_1(self):
        engine = self._air_glass()
        for angle in np.linspace(0, 89, 90):
            res = engine.calculate_coefficients(angle)
            for pol in ('TE', 'TM'):
                self.assertGreaterEqual(res[pol]['R'], 0.0)
                self.assertLessEqual(res[pol]['R'], 1.0 + 1e-9)
                self.assertGreaterEqual(res[pol]['T'], 0.0)
                self.assertLessEqual(res[pol]['T'], 1.0 + 1e-9)

    def test_absorption_zero_for_lossless(self):
        engine = self._air_glass()
        for angle in np.linspace(0, 80, 10):
            res = engine.calculate_coefficients(angle)
            self.assertAlmostEqual(res['TE']['A'], 0.0, places=5)
            self.assertAlmostEqual(res['TM']['A'], 0.0, places=5)


class TestLossyMediaAndEllipsometry(unittest.TestCase):

    def _lossy_engine(self, eps2_imag=1.0):
        return FresnelEngine(1.0, 1.0, complex(2.25, eps2_imag), 1.0)

    def _lossy_magnetic_engine(self, eps2_imag=1.0, mu2_imag=0.5):
        return FresnelEngine(1.0, 1.0, complex(2.25, eps2_imag), complex(1.0, mu2_imag))

    def test_energy_conservation_lossy_te(self):
        engine = self._lossy_engine(1.0)
        for angle in np.linspace(0, 85, 18):
            res = engine.calculate_coefficients(angle)
            total = res['TE']['R'] + res['TE']['T'] + res['TE']['A']
            self.assertAlmostEqual(total, 1.0, places=5)

    def test_energy_conservation_lossy_tm(self):
        engine = self._lossy_engine(1.0)
        for angle in np.linspace(0, 85, 18):
            res = engine.calculate_coefficients(angle)
            total = res['TM']['R'] + res['TM']['T'] + res['TM']['A']
            self.assertAlmostEqual(total, 1.0, places=5)

    def test_energy_conservation_highly_lossy(self):
        engine = self._lossy_engine(5.0)
        for angle in np.linspace(0, 85, 12):
            res = engine.calculate_coefficients(angle)
            for pol in ('TE', 'TM'):
                total = res[pol]['R'] + res[pol]['T'] + res[pol]['A']
                self.assertAlmostEqual(total, 1.0, places=5)

    def test_absorption_nonnegative_lossy(self):
        engine = self._lossy_engine(1.0)
        for angle in np.linspace(0, 85, 18):
            res = engine.calculate_coefficients(angle)
            for pol in ('TE', 'TM'):
                self.assertGreaterEqual(res[pol]['A'], 0.0)

    def test_energy_conservation_lossy_complex_mu(self):
        engine = self._lossy_magnetic_engine(1.0, 0.5)
        for angle in np.linspace(0, 85, 12):
            res = engine.calculate_coefficients(angle)
            for pol in ('TE', 'TM'):
                total = res[pol]['R'] + res[pol]['T'] + res[pol]['A']
                self.assertAlmostEqual(total, 1.0, places=5)

    def test_reflection_magnitude_bounded_lossy(self):
        engine = self._lossy_engine(2.0)
        for angle in np.linspace(0, 89, 90):
            res = engine.calculate_coefficients(angle)
            for pol in ('TE', 'TM'):
                self.assertLessEqual(abs(res[pol]['r']), 1.0 + 1e-9)

    def test_psi_zero_at_brewster_lossless(self):
        engine = FresnelEngine(1.0, 1.0, 2.25, 1.0)
        theta_b = engine.get_brewster_angle()
        res = engine.calculate_coefficients(theta_b)
        r_te = res['TE']['r']
        r_tm = res['TM']['r']
        psi = np.degrees(np.arctan2(abs(r_tm), abs(r_te)))
        self.assertAlmostEqual(psi, 0.0, places=3)

    def test_psi_45_at_normal_incidence_lossless(self):
        engine = FresnelEngine(1.0, 1.0, 2.25, 1.0)
        res = engine.calculate_coefficients(0)
        r_te = res['TE']['r']
        r_tm = res['TM']['r']
        psi = np.degrees(np.arctan2(abs(r_tm), abs(r_te)))
        self.assertAlmostEqual(psi, 45.0, places=3)

    def test_tir_r_equals_1(self):
        engine = FresnelEngine(2.25, 1.0, 1.0, 1.0)
        theta_c = engine.get_critical_angle()
        for pol in ('TE', 'TM'):
            res = engine.calculate_coefficients(theta_c + 10)
            self.assertAlmostEqual(res[pol]['R'], 1.0, places=4)
            self.assertAlmostEqual(res[pol]['T'], 0.0, places=4)
            self.assertAlmostEqual(res[pol]['A'], 0.0, places=4)


class TestThinFilm(unittest.TestCase):

    def _base_engine(self):
        return FresnelEngine(1.0, 1.0, 2.25, 1.0)

    def _lossy_film_spec(self):
        return {'eps': (2.0 + 0.1j) ** 2, 'mu': 1.0, 'thickness': 100.0}

    def _quarter_wave_engine(self):
        substrate_index = 1.5
        film_index = np.sqrt(substrate_index)
        wavelength = 550.0
        thickness = wavelength / (4 * film_index)
        engine = FresnelEngine(
            1.0, 1.0, substrate_index ** 2, 1.0,
            film={'eps': film_index ** 2, 'mu': 1.0, 'thickness': thickness},
            wavelength=wavelength
        )
        return engine, thickness

    def test_zero_thickness_preserves_interface_behaviour(self):
        base_engine = self._base_engine()
        zero_film_engine = FresnelEngine(
            1.0, 1.0, 2.25, 1.0,
            film={'eps': 1.9, 'mu': 1.0, 'thickness': 0.0},
            wavelength=550.0
        )
        for angle in (0, 20, 45, 70):
            base = base_engine.calculate_coefficients(angle)
            zero_film = zero_film_engine.calculate_coefficients(angle)
            for pol in ('TE', 'TM'):
                self.assertAlmostEqual(base[pol]['R'], zero_film[pol]['R'], places=7)
                self.assertAlmostEqual(base[pol]['T'], zero_film[pol]['T'], places=7)

    def test_energy_conservation_lossless_thin_film(self):
        engine, _ = self._quarter_wave_engine()
        for angle in np.linspace(0, 80, 12):
            res = engine.calculate_coefficients(angle)
            self.assertAlmostEqual(res['TE']['R'] + res['TE']['T'], 1.0, places=5)
            self.assertAlmostEqual(res['TM']['R'] + res['TM']['T'], 1.0, places=5)
            self.assertAlmostEqual(res['TE']['A'], 0.0, places=5)
            self.assertAlmostEqual(res['TM']['A'], 0.0, places=5)

    def test_energy_conservation_lossy_thin_film(self):
        engine = FresnelEngine(
            1.0, 1.0, 2.25, 1.0,
            film=self._lossy_film_spec(),
            wavelength=550.0,
        )
        positive = {'TE': False, 'TM': False}

        for angle in (0, 20, 45, 70):
            res = engine.calculate_coefficients(angle)
            for pol in ('TE', 'TM'):
                total = res[pol]['R'] + res[pol]['T'] + res[pol]['A']
                self.assertAlmostEqual(total, 1.0, places=5)
                self.assertGreaterEqual(res[pol]['A'], 0.0)
                positive[pol] = positive[pol] or res[pol]['A'] > 1e-6

        self.assertTrue(positive['TE'])
        self.assertTrue(positive['TM'])

    def test_quarter_wave_film_reduces_reflection_at_normal_incidence(self):
        base_engine = self._base_engine()
        film_engine, _ = self._quarter_wave_engine()

        base = base_engine.calculate_coefficients(0)
        film = film_engine.calculate_coefficients(0)

        self.assertLess(film['TE']['R'], base['TE']['R'])
        self.assertLess(film['TM']['R'], base['TM']['R'])
        self.assertAlmostEqual(film['TE']['R'], 0.0, places=6)
        self.assertAlmostEqual(film['TM']['R'], 0.0, places=6)
        self.assertAlmostEqual(film['TE']['T'], 1.0, places=6)
        self.assertAlmostEqual(film['TM']['T'], 1.0, places=6)

    def test_thin_film_reports_internal_angle(self):
        engine, thickness = self._quarter_wave_engine()
        res = engine.calculate_coefficients(30)

        self.assertIsNotNone(res['angles']['theta_film'])
        self.assertAlmostEqual(res['thin_film']['thickness'], thickness, places=6)
        self.assertAlmostEqual(res['thin_film']['wavelength'], 550.0, places=6)


class TestAbsorbance(unittest.TestCase):

    def test_absorbance_lossless_normal(self):
        engine = FresnelEngine(1.0, 1.0, 2.25, 1.0)
        res = engine.calculate_coefficients(0)
        expected_abs = -np.log10(0.96)
        self.assertAlmostEqual(res['TE']['Absorbance'], expected_abs, places=5)
        self.assertAlmostEqual(res['TM']['Absorbance'], expected_abs, places=5)

    def test_absorbance_perfect_transmission(self):
        engine = FresnelEngine(2.0, 1.0, 2.0, 1.0)
        res = engine.calculate_coefficients(45)
        self.assertAlmostEqual(res['TE']['Absorbance'], 0.0, places=7)
        self.assertAlmostEqual(res['TM']['Absorbance'], 0.0, places=7)

    def test_absorbance_tir(self):
        engine = FresnelEngine(2.25, 1.0, 1.0, 1.0)
        theta_c = engine.get_critical_angle()
        res = engine.calculate_coefficients(theta_c + 5)
        self.assertEqual(res['TE']['Absorbance'], float('inf'))
        self.assertEqual(res['TM']['Absorbance'], float('inf'))

    def test_absorbance_lossy_medium(self):
        engine = FresnelEngine(1.0, 1.0, complex(2.25, 1.0), 1.0)
        res = engine.calculate_coefficients(30)
        t_te = res['TE']['T']
        expected_abs = -np.log10(t_te) if t_te > 0 else float('inf')
        self.assertAlmostEqual(res['TE']['Absorbance'], expected_abs, places=7)


class TestUnpolarized(unittest.TestCase):

    def test_unpolarized_at_normal_incidence(self):
        engine = FresnelEngine(1.0, 1.0, 2.25, 1.0)
        res = engine.calculate_coefficients(0)
        self.assertAlmostEqual(res['unpolarized']['R'], res['TE']['R'], places=7)
        self.assertAlmostEqual(res['unpolarized']['R'], res['TM']['R'], places=7)

    def test_unpolarized_average_formula(self):
        engine = FresnelEngine(1.0, 1.0, 2.25, 1.0)
        res = engine.calculate_coefficients(45)
        expected_r = (res['TE']['R'] + res['TM']['R']) / 2
        expected_t = (res['TE']['T'] + res['TM']['T']) / 2
        self.assertAlmostEqual(res['unpolarized']['R'], expected_r, places=7)
        self.assertAlmostEqual(res['unpolarized']['T'], expected_t, places=7)

    def test_unpolarized_at_brewster(self):
        engine = FresnelEngine(1.0, 1.0, 2.25, 1.0)
        theta_b = engine.get_brewster_angle()
        res = engine.calculate_coefficients(theta_b)
        self.assertAlmostEqual(res['TM']['R'], 0.0, places=5)
        self.assertAlmostEqual(res['unpolarized']['R'], res['TE']['R'] / 2, places=5)

    def test_unpolarized_energy_conservation(self):
        engine_ll = FresnelEngine(1.0, 1.0, 2.25, 1.0)
        for angle in (0, 30, 60):
            res = engine_ll.calculate_coefficients(angle)
            total = res['unpolarized']['R'] + res['unpolarized']['T'] + res['unpolarized']['A']
            self.assertAlmostEqual(total, 1.0, places=5)
        engine_ly = FresnelEngine(1.0, 1.0, complex(2.25, 1.0), 1.0)
        for angle in (0, 30, 60):
            res = engine_ly.calculate_coefficients(angle)
            total = res['unpolarized']['R'] + res['unpolarized']['T'] + res['unpolarized']['A']
            self.assertAlmostEqual(total, 1.0, places=5)

    def test_unpolarized_thin_film(self):
        engine = FresnelEngine(
            1.0, 1.0, 2.25, 1.0,
            film={'eps': 1.9, 'mu': 1.0, 'thickness': 100.0},
            wavelength=550.0
        )
        res = engine.calculate_coefficients(30)
        self.assertIn('unpolarized', res)
        self.assertIn('R', res['unpolarized'])
        self.assertIn('T', res['unpolarized'])


class TestMultilayer(unittest.TestCase):

    def _single_lossy_layer(self):
        return {'eps': (2.0 + 0.1j) ** 2, 'mu': 1.0, 'thickness': 100.0}

    def test_zero_layers_equals_simple_interface(self):
        bare = FresnelEngine(1.0, 1.0, 2.25, 1.0)
        layered = FresnelEngine(1.0, 1.0, 2.25, 1.0, layers=[])
        for angle in (0, 30, 60):
            r1 = bare.calculate_coefficients(angle)
            r2 = layered.calculate_coefficients(angle)
            for pol in ('TE', 'TM'):
                self.assertAlmostEqual(r1[pol]['R'], r2[pol]['R'], places=7)
                self.assertAlmostEqual(r1[pol]['T'], r2[pol]['T'], places=7)

    def test_single_layer_matches_thin_film(self):
        film_spec = {'eps': 1.9, 'mu': 1.0, 'thickness': 100.0}
        engine_film = FresnelEngine(1.0, 1.0, 2.25, 1.0, film=film_spec, wavelength=550.0)
        engine_tmm = FresnelEngine(1.0, 1.0, 2.25, 1.0, layers=[film_spec], wavelength=550.0)
        for angle in (0, 20, 45, 70):
            r_film = engine_film.calculate_coefficients(angle)
            r_tmm = engine_tmm.calculate_coefficients(angle)
            for pol in ('TE', 'TM'):
                self.assertAlmostEqual(r_film[pol]['R'], r_tmm[pol]['R'], places=6)
                self.assertAlmostEqual(r_film[pol]['T'], r_tmm[pol]['T'], places=6)

    def test_single_absorbing_layer_matches_thin_film(self):
        film_spec = self._single_lossy_layer()
        engine_film = FresnelEngine(1.0, 1.0, 2.25, 1.0, film=film_spec, wavelength=550.0)
        engine_tmm = FresnelEngine(1.0, 1.0, 2.25, 1.0, layers=[film_spec], wavelength=550.0)
        for angle in (0, 20, 45, 70):
            r_film = engine_film.calculate_coefficients(angle)
            r_tmm = engine_tmm.calculate_coefficients(angle)
            for pol in ('TE', 'TM'):
                self.assertAlmostEqual(r_film[pol]['R'], r_tmm[pol]['R'], places=6)
                self.assertAlmostEqual(r_film[pol]['T'], r_tmm[pol]['T'], places=6)
                self.assertAlmostEqual(r_film[pol]['A'], r_tmm[pol]['A'], places=6)

    def test_energy_conservation_multilayer_lossless(self):
        layers = [
            {'eps': 2.0, 'mu': 1.0, 'thickness': 80.0},
            {'eps': 1.5, 'mu': 1.0, 'thickness': 120.0},
            {'eps': 2.3, 'mu': 1.0, 'thickness': 60.0},
        ]
        engine = FresnelEngine(1.0, 1.0, 2.25, 1.0, layers=layers, wavelength=550.0)
        for angle in (0, 15, 30, 45, 60, 75):
            res = engine.calculate_coefficients(angle)
            for pol in ('TE', 'TM'):
                total = res[pol]['R'] + res[pol]['T']
                self.assertAlmostEqual(total, 1.0, places=5)

    def test_dbr_high_reflectance(self):
        wl = 550.0
        n_H, n_L = 2.3, 1.38
        t_H = wl / (4 * n_H)
        t_L = wl / (4 * n_L)
        layers = []
        for _ in range(5):
            layers.append({'eps': n_H ** 2, 'mu': 1.0, 'thickness': t_H})
            layers.append({'eps': n_L ** 2, 'mu': 1.0, 'thickness': t_L})
        engine = FresnelEngine(1.0, 1.0, 2.25, 1.0, layers=layers, wavelength=wl)
        res = engine.calculate_coefficients(0)
        self.assertGreater(res['TE']['R'], 0.98)
        self.assertGreater(res['TM']['R'], 0.98)

    def test_energy_conservation_multilayer_lossy(self):
        layers = [
            {'eps': complex(2.0, 0.0001), 'mu': 1.0, 'thickness': 80.0},
            {'eps': 1.5, 'mu': 1.0, 'thickness': 120.0},
        ]
        engine = FresnelEngine(1.0, 1.0, 2.25, 1.0, layers=layers, wavelength=550.0)
        for angle in (0, 30, 60):
            res = engine.calculate_coefficients(angle)
            for pol in ('TE', 'TM'):
                total = res[pol]['R'] + res[pol]['T'] + res[pol]['A']
                self.assertAlmostEqual(total, 1.0, places=3)

    def test_single_absorbing_layer_has_positive_absorptance(self):
        engine = FresnelEngine(
            1.0, 1.0, 2.25, 1.0,
            layers=[self._single_lossy_layer()],
            wavelength=550.0,
        )
        positive = {'TE': False, 'TM': False}

        for angle in (0, 20, 45, 70):
            res = engine.calculate_coefficients(angle)
            for pol in ('TE', 'TM'):
                total = res[pol]['R'] + res[pol]['T'] + res[pol]['A']
                self.assertAlmostEqual(total, 1.0, places=5)
                self.assertGreaterEqual(res[pol]['A'], 0.0)
                positive[pol] = positive[pol] or res[pol]['A'] > 1e-6

        self.assertTrue(positive['TE'])
        self.assertTrue(positive['TM'])

    def test_multilayer_report(self):
        layers = [
            {'eps': 2.0, 'mu': 1.0, 'thickness': 80.0},
            {'eps': 1.5, 'mu': 1.0, 'thickness': 120.0},
        ]
        engine = FresnelEngine(1.0, 1.0, 2.25, 1.0, layers=layers, wavelength=550.0)
        res = engine.calculate_coefficients(0)
        self.assertIn('multilayer', res)
        self.assertEqual(res['multilayer']['num_layers'], 2)
        self.assertAlmostEqual(res['multilayer']['total_thickness'], 200.0, places=6)

    def test_fabry_perot_resonance(self):
        wl = 550.0
        n_spacer = 1.5
        t_spacer = wl / (2 * n_spacer)
        mirror = {'eps': complex(4.0, 0.0), 'mu': 1.0, 'thickness': 30.0}
        spacer = {'eps': n_spacer ** 2, 'mu': 1.0, 'thickness': t_spacer}
        layers = [mirror, spacer, mirror]
        engine = FresnelEngine(1.0, 1.0, 1.0, 1.0, layers=layers, wavelength=wl)
        res = engine.calculate_coefficients(0)
        self.assertGreater(res['TE']['T'], 0.3)


class TestDispersionModels(unittest.TestCase):

    def test_constant_model(self):
        model = ConstantModel(2.25)
        self.assertEqual(model.epsilon(400), 2.25)
        self.assertEqual(model.epsilon(700), 2.25)
        self.assertEqual(model.epsilon(1550), 2.25)

    def test_sellmeier_bk7(self):
        model = MATERIAL_PRESETS['BK7']
        n = np.real(model.n_complex(589.3))
        self.assertAlmostEqual(n, 1.5168, places=3)

    def test_sellmeier_fused_silica(self):
        model = MATERIAL_PRESETS['Fused Silica']
        n = np.real(model.n_complex(589.3))
        self.assertAlmostEqual(n, 1.458, places=2)

    def test_drude_negative_eps(self):
        model = DrudeModel(eps_inf=1.0, omega_p_eV=9.0, gamma_eV=0.05)
        eps = model.epsilon(800)
        self.assertLess(np.real(eps), 0)

    def test_drude_lorentz_gold(self):
        model = MATERIAL_PRESETS['Gold']
        eps = model.epsilon(633)
        self.assertLess(np.real(eps), -5)

    def test_material_presets_complete(self):
        expected = ['Air', 'BK7', 'Fused Silica', 'Water', 'Sapphire',
                    'Gold', 'Silver', 'Aluminum', 'Copper', 'Silicon']
        for name in expected:
            self.assertIn(name, MATERIAL_PRESETS)
            self.assertIsInstance(MATERIAL_PRESETS[name], DispersionModel)

    def test_cauchy_model(self):
        model = CauchyModel(A=1.5, B=0.005)
        n = np.real(model.n_complex(500))
        self.assertAlmostEqual(n, 1.52, places=2)


class TestSpectralCalculation(unittest.TestCase):

    def test_spectral_constant_matches_single(self):
        model1 = ConstantModel(1.0)
        model2 = ConstantModel(2.25)
        wl = np.array([550.0])
        spec = FresnelEngine.calculate_spectral(model1, 1.0, model2, 1.0, 30, wl)
        engine = FresnelEngine(1.0, 1.0, 2.25, 1.0)
        single = engine.calculate_coefficients(30)
        self.assertAlmostEqual(spec['R_TE'][0], single['TE']['R'], places=7)
        self.assertAlmostEqual(spec['R_TM'][0], single['TM']['R'], places=7)
        self.assertAlmostEqual(spec['T_TE'][0], single['TE']['T'], places=7)

    def test_spectral_gold_high_r_in_ir(self):
        gold = MATERIAL_PRESETS['Gold']
        air = ConstantModel(1.0)
        wls = np.linspace(700, 800, 5)
        spec = FresnelEngine.calculate_spectral(air, 1.0, gold, 1.0, 10, wls)
        for i in range(len(wls)):
            self.assertGreater(spec['R_unpol'][i], 0.9)

    def test_spectral_returns_correct_keys(self):
        model1 = ConstantModel(1.0)
        model2 = ConstantModel(2.25)
        wls = np.array([400.0, 550.0, 700.0])
        spec = FresnelEngine.calculate_spectral(model1, 1.0, model2, 1.0, 0, wls)
        for key in ('wavelengths', 'R_TE', 'R_TM', 'T_TE', 'T_TM', 'R_unpol', 'T_unpol'):
            self.assertIn(key, spec)
        self.assertEqual(len(spec['wavelengths']), 3)

    def test_spectral_with_layers(self):
        model1 = ConstantModel(1.0)
        model2 = ConstantModel(2.25)
        layers_spec = [{'model': ConstantModel(1.9), 'mu': 1.0, 'thickness': 100.0}]
        wls = np.array([500.0, 550.0, 600.0])
        spec = FresnelEngine.calculate_spectral(model1, 1.0, model2, 1.0, 0, wls,
                                                layers_spec=layers_spec)
        self.assertEqual(len(spec['R_TE']), 3)
        for i in range(3):
            total = spec['R_TE'][i] + spec['T_TE'][i]
            self.assertAlmostEqual(total, 1.0, places=4)


if __name__ == '__main__':
    unittest.main()
