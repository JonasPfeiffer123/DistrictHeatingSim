from PyQt5.QtCore import QThread, pyqtSignal
import traceback
from main import initialize_net_profile_calculation, thermohydraulic_time_series_net_calculation

class CalculationThread(QThread):
    calculation_done = pyqtSignal(object)
    calculation_error = pyqtSignal(str)

    def __init__(self, gdf_vl, gdf_rl, gdf_HAST, gdf_WEA, building_type, calc_method, calc1, calc2):
        super().__init__()
        self.gdf_vl = gdf_vl
        self.gdf_rl = gdf_rl
        self.gdf_HAST = gdf_HAST
        self.gdf_WEA = gdf_WEA
        self.building_type = building_type
        self.calc_method = calc_method
        self.calc1 = calc1
        self.calc2 = calc2

    def run(self):
        try:
            self.net, self.yearly_time_steps, self.waerme_ges_W = initialize_net_profile_calculation(self.gdf_vl, self.gdf_rl, self.gdf_HAST, self.gdf_WEA, self.building_type, self.calc_method)

            self.time_steps, self.net, self.net_results = thermohydraulic_time_series_net_calculation(self.net, self.yearly_time_steps, self.waerme_ges_W, self.calc1, self.calc2)

            self.calculation_done.emit(( self.time_steps, self.net, self.net_results))
        except Exception as e:
            self.calculation_error.emit(str(e) + "\n" + traceback.format_exc())

    def stop(self):
        if self.isRunning():
            self.requestInterruption()
            self.wait()  # Warten auf das sichere Beenden des Threads