# coding=utf-8

import hashlib
from audioprints.objects.Fingerprint import Fingerprint
from audioprints.objects.SpectogramPeak import SpectogramPeak
import numpy as np
import matplotlib.mlab as mlab
from scipy.ndimage import iterate_structure, generate_binary_structure, maximum_filter, binary_erosion

# Класс для снятия отпечатка с аудио каналов
class Extractor:

    # Константы
    DEFAULT_FREQUENCY_SPEED = 44100     # Количество снятий в секунду
    DEFAULT_WINDOW_SIZE = 4096          # Размер FFT окна
    DEFAULT_WINDOW_OVERLAP_RATIO = 0.5  # Соотношение, в котором следующее окно перекрывает предыдущее
    DEFAULT_FAN_VALUE = 15              # Градус, в котором отпечаток складывается в пару с его соседями
    DEFAULT_MIN_AMPLITUDE = 20          # Минимальная амплитуда, при которой она считается пиком
    PEAK_NEIGHBORHOOD_SIZE = 20         # Количество ячеек возде амплитудного пика
    MIN_HASH_TIME_DELTA = 0             # Порог, показывающий, как близко отпечаток должен быть к другому, чтобы оказаться в паре
    MAX_HASH_TIME_DELTA = 200           # Порог, показывающий, как далеко отпечаток должен быть к другому, чтобы оказаться в паре

    def __init__(self):
        pass

    # Получает отпечаток по экземплярам
    @staticmethod
    def extractFingerprints(frequencies, song_id = 0, frame_rate = DEFAULT_FREQUENCY_SPEED, window_size = DEFAULT_WINDOW_SIZE, window_overlap_ration = DEFAULT_WINDOW_OVERLAP_RATIO, fan_value = DEFAULT_FAN_VALUE, minimum_amplitude = DEFAULT_MIN_AMPLITUDE):
        spectrogram = Extractor._generateSpectrogram(frequencies, frame_rate, window_overlap_ration, window_size)
        peaks = Extractor._findPeaks(spectrogram, minimum_amplitude)
        fingerprints = Extractor._generateFingerprintsFromPeaks(peaks, song_id, fan_value)

        return fingerprints

    # Получает пики по экземплярам
    @staticmethod
    def extractPeaks(frequencies, frame_rate = DEFAULT_FREQUENCY_SPEED, window_size = DEFAULT_WINDOW_SIZE, window_overlap_ration = DEFAULT_WINDOW_OVERLAP_RATIO, minimum_amplitude = DEFAULT_MIN_AMPLITUDE):
        spectrogram = Extractor._generateSpectrogram(frequencies, frame_rate, window_overlap_ration, window_size)
        peaks = Extractor._findPeaks(spectrogram, minimum_amplitude)

        return peaks

    # Получает Спектограмму по экземплярам
    @staticmethod
    def extractSpectogram(frequencies, frame_rate = DEFAULT_FREQUENCY_SPEED, window_size = DEFAULT_WINDOW_SIZE, window_overlap_ration = DEFAULT_WINDOW_OVERLAP_RATIO):
        spectrogram = Extractor._generateSpectrogram(frequencies, frame_rate, window_overlap_ration, window_size)

        return spectrogram

    # Генерирует мпектограмму по массиву частот
    @staticmethod
    def _generateSpectrogram(frequencies, frame_rate, window_overlap_ration, window_size):
        spectrogram = mlab.specgram(frequencies, NFFT=window_size, Fs=frame_rate, window=mlab.window_hanning, noverlap=int(window_size * window_overlap_ration))[0]

        spectrogram = 10 * np.log10(spectrogram)    # Применяем трансформацию, т.к. specgram возвращает линейный массив
        spectrogram[spectrogram == -np.inf] = 0     # Заменяем бесконечности нулями

        return spectrogram

    # Находит пики в спектограмме
    @staticmethod
    def _findPeaks(spectrogram, min_amplitude = DEFAULT_MIN_AMPLITUDE):
        # Находим локальные максимумы, используя binary_erosion
        neighbourhood_structure = generate_binary_structure(2, 1)
        neighborhood = iterate_structure(neighbourhood_structure, Extractor.PEAK_NEIGHBORHOOD_SIZE)
        local_max = maximum_filter(spectrogram, footprint=neighborhood) == spectrogram
        background = (spectrogram == 0)
        eroded_background = binary_erosion(background, structure=neighborhood, border_value=1)
        detected_peaks = local_max - eroded_background

        # Формируем массив пик
        peak_amplitudes = spectrogram[detected_peaks].flatten()
        peak_frequencies, peak_times = np.where(detected_peaks)
        raw_peaks = []
        for i in range(0, min(peak_amplitudes.size, peak_frequencies.size, peak_times.size)):
            raw_peaks.append(SpectogramPeak(peak_frequencies[i], peak_times[i], peak_amplitudes[i]))

        # Выбираем только пики с нормальной для нас амплитудой
        peaks = [peak for peak in raw_peaks if peak.amplitude > min_amplitude]

        return peaks

    # Генерирует хеши по пикам
    @staticmethod
    def _generateFingerprintsFromPeaks(peaks, song_id, fan_value=DEFAULT_FAN_VALUE):
        for i in range(len(peaks)):
            for j in range(1, fan_value):
                if (i + j) < len(peaks):
                    time_delta = peaks[i + j].time - peaks[i].time

                    # Если находится рядом, генерируем для пары хеш
                    if Extractor.MIN_HASH_TIME_DELTA <= time_delta <= Extractor.MAX_HASH_TIME_DELTA:
                        hashed = hashlib.sha1("%s|%s|%s" % (str(peaks[i].frequency), str(peaks[i + j].frequency), str(time_delta)))
                        yield Fingerprint(song_id, peaks[i].time, hashed.hexdigest())
