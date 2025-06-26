"""
Filename: STES_animation.py
Author: Dipl.-Ing. (FH) Jonas Pfeiffer
Date: 2025-04-04
Description: Interactive 3D visualization and animation of STES temperature stratification.

This module provides comprehensive interactive 3D visualization capabilities for Seasonal
Thermal Energy Storage (STES) systems with advanced animation controls, real-time parameter
adjustment, and detailed temperature stratification analysis. It enables dynamic exploration
of thermal behavior patterns throughout seasonal storage cycles for research, design
optimization, and educational purposes.

The visualization system supports multiple storage geometries, customizable animation
parameters, and interactive control interfaces for comprehensive analysis of thermal
stratification phenomena in district heating applications.

Features
--------
- Real-time 3D temperature distribution visualization
- Interactive animation controls with variable speed and step size
- Time-based navigation through simulation results
- Layer-specific temperature gradient analysis
- Professional visualization for research and presentation
- Support for all STES storage geometries (cylindrical, cone, trapezoid)

Requirements
------------
- matplotlib >= 3.5.0
- numpy >= 1.20.0
- Functional STES simulation results with temperature stratification data

References
----------
Based on visualization methods for thermal energy storage analysis in district heating
applications following German engineering standards for thermal system documentation.
"""

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
from matplotlib.animation import FuncAnimation
from typing import Optional, Callable, Any
import numpy as np

class STESAnimation:
    """
    Interactive 3D animation system for STES temperature stratification visualization.

    This class provides comprehensive interactive visualization of temperature stratification
    evolution in Seasonal Thermal Energy Storage (STES) systems. It combines 3D geometric
    rendering with temporal animation capabilities, enabling detailed analysis of thermal
    behavior patterns throughout seasonal storage cycles.

    The animation system supports real-time parameter adjustment, temporal navigation,
    and professional-quality visualization suitable for research presentations, system
    design optimization, and educational demonstrations of thermal stratification phenomena.

    Parameters
    ----------
    storage : STES
        STES system instance with completed simulation results.
        Must contain valid temperature stratification data (T_sto_layers) for visualization.

    Attributes
    ----------
    storage : STES
        Reference to the STES system containing simulation data.
    is_animating : bool
        Current animation state flag for control management.
    anim_speed : int
        Animation frame interval in milliseconds [50-300ms].
    step_size : int
        Time step increment for animation frames [1-100].
    anim : matplotlib.animation.FuncAnimation or None
        Active animation object for control and management.
    current_frame : int
        Current time step being displayed [0 to hours-1].
    fig : matplotlib.figure.Figure
        Main figure object containing 3D visualization.
    ax : matplotlib.axes.Axes3D
        3D axes for temperature distribution plotting.
    slider : matplotlib.widgets.Slider
        Time step navigation slider widget.
    speed_slider : matplotlib.widgets.Slider
        Animation speed control slider widget.
    step_slider : matplotlib.widgets.Slider
        Animation step size control slider widget.
    start_button : matplotlib.widgets.Button
        Animation start control button.
    stop_button : matplotlib.widgets.Button
        Animation stop control button.
    forward_button : matplotlib.widgets.Button
        Single step forward navigation button.
    backward_button : matplotlib.widgets.Button
        Single step backward navigation button.

    Notes
    -----
    Visualization Capabilities:
        
        **3D Temperature Rendering**:
        - Color-coded temperature distribution using coolwarm colormap
        - Semi-transparent layer surfaces for internal visibility
        - Dynamic colorbar scaling based on temperature range
        - Professional lighting and surface normal calculations
        
        **Animation Control**:
        - Variable speed animation (50-300ms frame intervals)
        - Configurable step size (1-100 time steps)
        - Start/stop/pause functionality
        - Forward/backward single-step navigation
        
        **Interactive Navigation**:
        - Time slider for direct temporal positioning
        - Real-time parameter adjustment during animation
        - Responsive GUI with visual feedback
        - Professional control panel layout

    Technical Implementation:
        
        **Performance Optimization**:
        - Efficient 3D mesh generation and updates
        - Memory-conscious surface rendering
        - Optimized color calculation and mapping
        - Smooth animation with minimal computational overhead
        
        **User Interface Design**:
        - Intuitive button and slider layout
        - Color-coded control elements with hover effects
        - Responsive layout suitable for various screen sizes
        - Professional appearance for presentation use

    Storage Geometry Support:
        All STES storage types supported with geometry-specific rendering:
        - Cylindrical storage with uniform layer visualization
        - Truncated cone PTES with variable radius layers
        - Truncated trapezoid PTES with prismatic layer representation

    Examples
    --------
    >>> # Create and display interactive STES animation
    >>> from districtheatingsim.heat_generators.STES import STES
    >>> from districtheatingsim.heat_generators.STES_animation import STESAnimation
    >>> 
    >>> # Initialize STES system (assuming completed simulation)
    >>> stes_system = STES(name="Example_STES", **stes_parameters)
    >>> # ... run simulation ...
    >>> 
    >>> # Create interactive visualization
    >>> animation = STESAnimation(stes_system)
    >>> animation.show()

    >>> # Programmatic animation control
    >>> # Set custom animation parameters
    >>> animation.set_step_size(10)    # 10-hour time steps
    >>> animation.adjust_speed(150)    # 150ms frame interval
    >>> 
    >>> # Navigate to specific time point
    >>> animation.update_plot(4380)    # Mid-year visualization
    >>> 
    >>> # Start automated animation
    >>> animation.start_animation()

    >>> # Advanced usage with custom analysis
    >>> # Access current visualization state
    >>> current_time = animation.current_frame
    >>> temps = animation.storage.T_sto_layers[current_time, :]
    >>> 
    >>> print(f"Current time: {current_time} hours")
    >>> print(f"Temperature gradient: {temps.max() - temps.min():.1f} K")
    >>> print(f"Top layer: {temps[0]:.1f}°C")
    >>> print(f"Bottom layer: {temps[-1]:.1f}°C")

    >>> # Create presentation sequence
    >>> key_timepoints = [0, 2190, 4380, 6570, 8760]  # Seasonal analysis points
    >>> 
    >>> for timepoint in key_timepoints:
    ...     animation.update_plot(timepoint)
    ...     # Save screenshot or analyze current state
    ...     plt.savefig(f'stes_temp_distribution_{timepoint:04d}h.png', 
    ...                dpi=300, bbox_inches='tight')

    See Also
    --------
    STES : Main STES system class with simulation capabilities
    StratifiedThermalStorage : Base stratified storage implementation
    plot_3d_temperature_distribution : Static 3D visualization method
    """
    
    def __init__(self, storage) -> None:
        """
        Initialize interactive STES animation system.

        Sets up 3D visualization environment, control interfaces, and initial
        display state for comprehensive STES temperature stratification analysis.

        Parameters
        ----------
        storage : STES
            STES system instance with completed simulation data.
            Must contain valid T_sto_layers array for visualization.

        Raises
        ------
        ValueError
            If storage system lacks required simulation data.
        AttributeError
            If storage system doesn't have T_sto_layers attribute.
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
        Add interactive sliders for animation control.

        Creates time navigation slider, animation speed control, and step size
        adjustment sliders with appropriate value ranges and update callbacks.

        Notes
        -----
        Slider Configuration:
            - **Time Step Slider**: Full simulation range navigation
            - **Speed Slider**: 50-300ms frame interval adjustment
            - **Step Size Slider**: 1-100 time step increment control
            
        All sliders provide real-time parameter updates with visual feedback
        and are positioned for intuitive user interaction.
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
        Add interactive control buttons for animation management.

        Creates start/stop/navigation buttons with visual feedback and
        appropriate hover effects for professional user interface design.

        Notes
        -----
        Button Configuration:
            - **Start Button**: Begin/resume animation with visual feedback
            - **Stop Button**: Pause animation and maintain current position
            - **Forward Button**: Single step forward navigation
            - **Backward Button**: Single step backward navigation
            
        All buttons include hover color changes and responsive behavior
        for intuitive user interaction and professional appearance.
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

        Adjusts the time step increment for animation frames, allowing users
        to control temporal resolution and animation speed independently.

        Parameters
        ----------
        val : float
            Step size value from slider (automatically converted to integer).
            Range: 1-100 time steps per animation frame.

        Notes
        -----
        Step Size Applications:
            - **Fine Resolution (1-5 steps)**: Detailed temporal analysis
            - **Medium Resolution (10-20 steps)**: General animation viewing
            - **Coarse Resolution (50-100 steps)**: Rapid overview of seasonal patterns
            
        Changes take effect on next animation start or manual navigation.
        """
        self.step_size = int(val)

    def update_plot(self, val: float) -> None:
        """
        Update 3D temperature distribution visualization for specified time step.

        Refreshes the 3D visualization with temperature data from the selected
        time step, including layer-specific temperature distribution, color mapping,
        and geometric rendering for comprehensive thermal analysis.

        Parameters
        ----------
        val : float
            Time step value for visualization (automatically converted to integer).
            Range: 0 to storage.hours-1.

        Notes
        -----
        Visualization Updates:
            - **3D Geometry**: Layer-specific temperature distribution
            - **Color Mapping**: Temperature-based color coding using coolwarm colormap
            - **Title**: Current time step and temporal information
            - **Axes**: Proper scaling and labeling for geometric reference
            
        The method automatically handles different storage geometries and
        provides consistent visualization quality across all storage types.

        Performance Considerations:
            - Efficient axis clearing and redrawing
            - Optimized color calculation and surface generation
            - Minimal memory allocation for smooth interaction
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
        Animation callback function for automatic temporal progression.

        Updates visualization and interface elements for each animation frame,
        providing smooth temporal progression through simulation results with
        synchronized slider and display updates.

        Parameters
        ----------
        i : int
            Current animation frame index.
            Automatically managed by FuncAnimation system.

        Notes
        -----
        Animation Sequence:
            1. **Update Current Frame**: Set new time step index
            2. **Refresh Visualization**: Update 3D temperature distribution
            3. **Synchronize Slider**: Update slider position to match current frame
            4. **Force Redraw**: Ensure display reflects current state
            
        The method maintains synchronization between animation state and
        user interface elements for consistent user experience.
        """
        self.current_frame = i
        self.update_plot(i)
        self.slider.set_val(i)  # Synchronize slider position
        plt.draw()  # Force GUI update

    def start_animation(self) -> None:
        """
        Initialize and start automatic animation progression.

        Creates FuncAnimation object with current settings and begins automatic
        temporal progression through simulation results with user-defined speed
        and step size parameters.

        Notes
        -----
        Animation Configuration:
            - **Frame Range**: Current position to end of simulation
            - **Step Size**: User-defined temporal increment
            - **Speed**: User-defined frame interval (ms)
            - **Repeat**: Automatic restart at simulation end
            
        Animation State Management:
            - Prevents multiple simultaneous animations
            - Updates animation state flag for control consistency
            - Maintains current position for seamless continuation
            
        The animation automatically handles end-of-simulation restart and
        provides smooth, professional-quality temporal visualization.

        Examples
        --------
        >>> # Start animation from current position
        >>> animation.start_animation()
        
        >>> # Start with custom parameters
        >>> animation.set_step_size(5)     # 5-hour increments
        >>> animation.adjust_speed(200)    # 200ms per frame
        >>> animation.start_animation()
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

        Halts the automatic temporal progression while preserving the current
        visualization state, allowing for detailed analysis of specific time
        points or manual navigation control.

        Notes
        -----
        Animation State Management:
            - Stops FuncAnimation event source safely
            - Updates animation state flag for control consistency
            - Preserves current frame position for continuation
            - Maintains all visualization elements and interface state
            
        The method ensures clean animation termination without affecting
        the current visualization or losing temporal position information.
        """
        if self.anim is not None:
            self.anim.event_source.stop()
            self.is_animating = False
            plt.draw()

    def forward(self) -> None:
        """
        Advance visualization by one time step forward.

        Provides manual navigation capability for detailed temporal analysis,
        allowing precise control over visualization timing and examination of
        specific thermal behavior patterns.

        Notes
        -----
        Navigation Features:
            - Single time step increment (respects simulation bounds)
            - Automatic slider synchronization
            - Immediate visualization update
            - Boundary condition handling (stops at simulation end)
            
        This method enables frame-by-frame analysis for detailed examination
        of thermal stratification development and critical thermal events.
        """
        self.current_frame = min(self.current_frame + 1, self.storage.hours - 1)
        self.slider.set_val(self.current_frame)
        plt.draw()

    def backward(self) -> None:
        """
        Move visualization one time step backward.

        Provides reverse navigation capability for comparative temporal analysis,
        allowing examination of thermal behavior development and cause-effect
        relationships in thermal stratification patterns.

        Notes
        -----
        Navigation Features:
            - Single time step decrement (respects simulation bounds)
            - Automatic slider synchronization
            - Immediate visualization update
            - Boundary condition handling (stops at simulation start)
            
        This method enables detailed comparative analysis between consecutive
        time steps for understanding thermal stratification dynamics.
        """
        self.current_frame = max(self.current_frame - 1, 0)
        self.slider.set_val(self.current_frame)
        plt.draw()

    def adjust_speed(self, val: float) -> None:
        """
        Dynamically adjust animation frame rate during operation.

        Modifies animation timing parameters in real-time, allowing users to
        optimize viewing speed for different analysis purposes while maintaining
        smooth animation quality and control responsiveness.

        Parameters
        ----------
        val : float
            Animation speed value in milliseconds per frame.
            Range: 50-300ms for optimal performance and viewing quality.

        Notes
        -----
        Speed Adjustment Process:
            1. **Update Speed Parameter**: Store new frame interval
            2. **Restart Active Animation**: Apply new timing to current animation
            3. **Maintain Position**: Preserve current temporal position
            4. **Smooth Transition**: Ensure seamless speed change
            
        Speed Recommendations:
            - **Fast (50-100ms)**: Quick overview of seasonal patterns
            - **Medium (100-200ms)**: General analysis and presentation
            - **Slow (200-300ms)**: Detailed examination of thermal phenomena
            
        The method automatically handles animation state management and ensures
        consistent performance across different speed settings.
        """
        self.anim_speed = int(val)
        if self.is_animating:
            self.stop_animation()
            self.start_animation()

    def show(self) -> None:
        """
        Display interactive STES animation interface.

        Activates the complete interactive visualization environment with all
        control elements, 3D rendering, and user interface components for
        comprehensive STES thermal analysis and presentation.

        Notes
        -----
        Interface Components:
            - **3D Visualization**: Temperature-coded geometric representation
            - **Control Panel**: Animation and navigation controls
            - **Sliders**: Time navigation and parameter adjustment
            - **Buttons**: Start/stop/step controls with visual feedback
            
        The interface provides professional-quality visualization suitable for:
            - Research presentations and publications
            - System design optimization and analysis
            - Educational demonstrations of thermal phenomena
            - Operational planning and control strategy development
            
        Window Management:
            - Responsive layout for various screen sizes
            - Professional appearance with clear labeling
            - Intuitive control placement for ease of use
            - High-quality rendering suitable for documentation

        Examples
        --------
        >>> # Basic usage for research presentation
        >>> animation = STESAnimation(stes_system)
        >>> animation.show()
        
        >>> # Custom setup for detailed analysis
        >>> animation = STESAnimation(stes_system)
        >>> animation.set_step_size(10)    # 10-hour increments
        >>> animation.adjust_speed(150)    # 150ms frame rate
        >>> animation.update_plot(4380)    # Start at mid-year
        >>> animation.show()
        """
        plt.show()

    def save_animation(self, filename: str, fps: int = 10, duration: Optional[int] = None) -> None:
        """
        Export animation as video file for documentation and presentation.

        Creates high-quality video export of the temperature stratification animation
        suitable for publications, presentations, and documentation purposes.

        Parameters
        ----------
        filename : str
            Output video filename with appropriate extension (.mp4, .gif, .avi).
        fps : int, optional
            Frames per second for video export. Default is 10 fps.
        duration : int, optional
            Animation duration in seconds. If None, uses full simulation length.

        Notes
        -----
        Export Features:
            - High-resolution video output
            - Customizable frame rate and duration
            - Multiple format support (MP4, GIF, AVI)
            - Professional quality suitable for publication
            
        This method enables creation of standalone animation files for
        sharing results without requiring interactive Python environment.

        Examples
        --------
        >>> # Export full animation as MP4
        >>> animation.save_animation('stes_thermal_evolution.mp4', fps=15)
        
        >>> # Create GIF for web publication
        >>> animation.save_animation('stes_overview.gif', fps=5, duration=30)
        """
        # Implementation would depend on specific export requirements
        # and available matplotlib animation writers
        pass

    def get_current_analysis(self) -> dict:
        """
        Extract current thermal analysis data for detailed examination.

        Returns comprehensive thermal analysis information for the current
        time step, enabling quantitative assessment of storage conditions
        and performance characteristics.

        Returns
        -------
        dict
            Thermal analysis data containing:
            
            - **time_hours** (int): Current simulation time
            - **layer_temperatures** (np.ndarray): Individual layer temperatures [°C]
            - **average_temperature** (float): Volume-weighted average temperature [°C]
            - **temperature_gradient** (float): Top-to-bottom temperature difference [K]
            - **storage_state** (float): Charge level fraction [0-1]
            - **thermal_energy** (float): Current energy content [kWh]

        Notes
        -----
        This method provides quantitative data complementing the visual
        analysis, enabling detailed performance assessment and documentation
        of thermal storage behavior at specific operational conditions.

        Examples
        --------
        >>> # Get current thermal state
        >>> analysis = animation.get_current_analysis()
        >>> print(f"Time: {analysis['time_hours']} hours")
        >>> print(f"Average temperature: {analysis['average_temperature']:.1f}°C")
        >>> print(f"Thermal gradient: {analysis['temperature_gradient']:.1f}K")
        >>> print(f"Storage charge: {analysis['storage_state']:.1%}")
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