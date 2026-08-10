"""App theme and matplotlib/seaborn styling."""

import matplotlib.pyplot as plt
import seaborn as sns

GREEN = "#7ED957"
NAVY = "#0D243B"
GRID = "#2F5175"
TEXT = "#E6F2F0"
LINE = "#E4E1E1C1"
RED = "#F87171"


def configure_plot_theme() -> None:
    plt.style.use("dark_background")
    sns.set_theme(
        style="darkgrid",
        rc={
            "axes.facecolor": NAVY,
            "figure.facecolor": NAVY,
            "grid.color": GRID,
            "axes.edgecolor": GRID,
            "axes.labelcolor": TEXT,
            "xtick.color": LINE,
            "ytick.color": LINE,
            "text.color": TEXT,
            "legend.frameon": False,
        },
    )
