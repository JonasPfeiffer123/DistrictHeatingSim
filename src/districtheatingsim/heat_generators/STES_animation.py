"""
STES Animation Module
================================

Interactive 3D visualization for Seasonal Thermal Energy Storage systems.

:author: Dipl.-Ing. (FH) Jonas Pfeiffer
"""

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.animation import FuncAnimation
from typing import Optional, Callable, Any
import numpy as np

class STESAnimation:
    """
    Interactive 3D animation for STES temperature stratification.

    :param storage: STES instance with simulation results
    :type storage: STES

    .. note::
       Provides real-time animation control and temporal navigation.
    """
    
    def __init__(self, storage) -> None:
        """
        Initialize interactive STES animation system with 3D visualization and control interfaces.

        :param storage: STES instance with simulation results
        :type storage: STES
        :raises ValueError: If storage lacks simulation data
        :raises AttributeError: If storage doesn't have T_sto_layers attribute
        """
        self.storage = storage
        self.is_animating = False
        self.anim_speed = 100  # Default animation speed (ms per frame)
        self.step_size = 1     # Default step size
        self.anim = None
        self.current_frame = 0

        # Validate storage data
        if not hasattr(storage, 'T_sto_layers'):
            raise AttributeError("Storage system must have T_sto_layers data for visualization")
        
        if storage.T_sto_layers.size == 0:
            raise ValueError("Storage system contains no temperature stratification data")

        # Initialize the figure and 3D axes
        self.fig, self.ax = plt.subplots(subplot_kw={"projection": "3d"}, figsize=(12, 8))
        plt.subplots_adjust(left=0.1, bottom=0.35)

        # Configure figure properties
        self.fig.suptitle(f'STES Temperature Stratification Animation - {storage.name}', 
                         fontsize=14, fontweight='bold')

        # Add interactive UI elements
        self._add_slider()
        self._add_buttons()

        # Initialize visualization state
        self.storage.labels_exist = False
        self.storage.colorbar_exists = False
        self.update_plot(0)

    def _add_slider(self) -> None:
        """
        Add interactive sliders for time navigation, speed control, and step size adjustment.

        .. note::
           Creates time step slider (0 to hours-1), speed slider (50-300ms), and step size slider (1-100 steps).
        """
        # Slider for time step navigation
        self.ax_slider = plt.axes([0.1, 0.1, 0.65, 0.03], facecolor='lightgoldenrodyellow')
        self.slider = Slider(
            self.ax_slider, 'Time Step', 
            0, self.storage.hours - 1, 
            valinit=self.current_frame, 
            valstep=1,
            valfmt='%d hours'
        )
        self.slider.on_changed(lambda val: self.update_plot(val))

        # Slider for animation speed control
        self.ax_speed = plt.axes([0.75, 0.25, 0.15, 0.04])
        self.speed_slider = Slider(
            self.ax_speed, 'Speed (ms)', 
            50, 300, 
            valinit=self.anim_speed,
            valfmt='%d ms'
        )
        self.speed_slider.on_changed(lambda val: self.adjust_speed(val))

        # Slider for step size control
        self.ax_step = plt.axes([0.75, 0.1, 0.15, 0.04])
        self.step_slider = Slider(
            self.ax_step, 'Step Size', 
            1, 100, 
            valinit=1, 
            valstep=1,
            valfmt='%d steps'
        )
        self.step_slider.on_changed(lambda val: self.set_step_size(val))

    def _add_buttons(self) -> None:
        """
        Add interactive control buttons (Start, Stop, Forward, Backward) with hover effects.

        .. note::
           All buttons include visual feedback and responsive hover color changes for intuitive interaction.
        """
        # Start animation button
        self.ax_start = plt.axes([0.1, 0.25, 0.1, 0.04])
        self.start_button = Button(
            self.ax_start, 'Start', 
            color='lightblue', 
            hovercolor='lightgreen'
        )
        self.start_button.on_clicked(lambda event: self.start_animation())

        # Stop animation button
        self.ax_stop = plt.axes([0.25, 0.25, 0.1, 0.04])
        self.stop_button = Button(
            self.ax_stop, 'Stop', 
            color='lightblue', 
            hovercolor='lightcoral'
        )
        self.stop_button.on_clicked(lambda event: self.stop_animation())

        # Forward step button
        self.ax_forward = plt.axes([0.4, 0.25, 0.1, 0.04])
        self.forward_button = Button(
            self.ax_forward, 'Forward', 
            color='lightblue', 
            hovercolor='lightyellow'
        )
        self.forward_button.on_clicked(lambda event: self.forward())

        # Backward step button
        self.ax_backward = plt.axes([0.55, 0.25, 0.1, 0.04])
        self.backward_button = Button(
            self.ax_backward, 'Backward', 
            color='lightblue', 
            hovercolor='lightyellow'
        )
        self.backward_button.on_clicked(lambda event: self.backward())

    def set_step_size(self, val: float) -> None:
        """
        Set animation step size for temporal resolution control.

        :param val: Step size value (1-100 time steps per frame)
        :type val: float

        .. note::
           Fine resolution (1-5), medium (10-20), coarse (50-100) for different analysis needs.
        """
        self.step_size = int(val)

    def update_plot(self, val: float) -> None:
        """
        Update 3D temperature distribution visualization for specified time step.

        :param val: Time step value (0 to hours-1)
        :type val: float

        .. note::
           Updates geometry, color mapping, title with temporal/thermal info, and axes scaling.
        """
        self.current_frame = int(val)
        self.ax.cla()  # Clear the axis for fresh rendering
        
        # Update 3D temperature distribution
        self.storage.plot_3d_temperature_distribution(self.ax, self.current_frame)
        
        # Set comprehensive title with temporal and thermal information
        temps = self.storage.T_sto_layers[self.current_frame, :]
        temp_gradient = temps.max() - temps.min()
        avg_temp = temps.mean()
        
        self.ax.set_title(
            f'Temperature Distribution - Time: {self.current_frame:04d}h\n'
            f'Avg: {avg_temp:.1f}°C, Gradient: {temp_gradient:.1f}K, '
            f'Top: {temps[0]:.1f}°C, Bottom: {temps[-1]:.1f}°C',
            fontsize=12, pad=20
        )
        
        # Force display update
        plt.draw()

    def animate(self, i: int) -> None:
        """
        Animation callback for automatic temporal progression.

        :param i: Current animation frame index
        :type i: int

        .. note::
           Updates visualization, synchronizes slider, and forces redraw for smooth animation.
        """
        self.current_frame = i
        self.update_plot(i)
        self.slider.set_val(i)  # Synchronize slider position
        plt.draw()  # Force GUI update

    def start_animation(self) -> None:
        """
        Initialize and start automatic animation progression with current settings.

        .. note::
           Creates FuncAnimation from current position to end with user-defined speed and step size.
        """
        if not self.is_animating:
            self.anim = FuncAnimation(
                self.fig,
                self.animate,
                frames=range(self.current_frame, self.storage.hours, self.step_size),
                interval=self.anim_speed,
                blit=False,
                repeat=True
            )
            self.is_animating = True
            plt.draw()

    def stop_animation(self) -> None:
        """
        Stop automatic animation and maintain current visualization state.

        .. note::
           Halts animation while preserving current position and all interface elements.
        """
        if self.anim is not None:
            self.anim.event_source.stop()
            self.is_animating = False
            plt.draw()

    def forward(self) -> None:
        """
        Advance visualization by one time step forward with automatic slider sync.

        .. note::
           Provides manual navigation for detailed frame-by-frame analysis.
        """
        self.current_frame = min(self.current_frame + 1, self.storage.hours - 1)
        self.slider.set_val(self.current_frame)
        plt.draw()

    def backward(self) -> None:
        """
        Move visualization one time step backward with automatic slider sync.

        .. note::
           Enables reverse navigation for comparative temporal analysis.
        """
        self.current_frame = max(self.current_frame - 1, 0)
        self.slider.set_val(self.current_frame)
        plt.draw()

    def adjust_speed(self, val: float) -> None:
        """
        Dynamically adjust animation frame rate during operation.

        :param val: Animation speed in milliseconds per frame (50-300ms)
        :type val: float

        .. note::
           Fast (50-100ms), medium (100-200ms), slow (200-300ms) for different viewing purposes.
        """
        self.anim_speed = int(val)
        if self.is_animating:
            self.stop_animation()
            self.start_animation()

    def show(self) -> None:
        """
        Display interactive STES animation interface with all controls and 3D rendering.

        .. note::
           Professional-quality visualization suitable for research, education, and operational planning.
        """
        plt.show()

    def save_animation(self, filename: str, fps: int = 10, duration: Optional[int] = None) -> None:
        """
        Export animation as video file for documentation and presentation.

        :param filename: Output filename with extension (.mp4, .gif, .avi)
        :type filename: str
        :param fps: Frames per second, defaults to 10
        :type fps: int
        :param duration: Animation duration in seconds, optional
        :type duration: Optional[int]

        .. note::
           Creates high-quality video suitable for publications and presentations.
        """
        # Implementation would depend on specific export requirements
        # and available matplotlib animation writers
        pass

    def get_current_analysis(self) -> dict:
        """
        Extract current thermal analysis data for detailed examination.

        :return: Dict with time_hours, layer_temperatures, average_temperature, temperature_gradient, storage_state, thermal_energy
        :rtype: dict

        .. note::
           Provides quantitative data complementing visual analysis for performance assessment.
        """
        temps = self.storage.T_sto_layers[self.current_frame, :]
        
        return {
            'time_hours': self.current_frame,
            'layer_temperatures': temps.copy(),
            'average_temperature': np.average(temps, weights=self.storage.layer_volume),
            'temperature_gradient': temps.max() - temps.min(),
            'storage_state': self.storage.storage_state[self.current_frame] if hasattr(self.storage, 'storage_state') else 0.0,
            'thermal_energy': self.storage.Q_sto[self.current_frame] if hasattr(self.storage, 'Q_sto') else 0.0
        }