"""Ryo palette (from ryoPorto.jpg) - single source of truth for all charts.

Identity colors only: no color ever encodes good/bad. Yellow = highlight.
"""

RYO = {
    "blue": "#5276C6",       # primary: backgrounds accents, headers
    "yellow": "#FAE965",     # highlight only (selected port, callout boxes)
    "black": "#000000",      # text, official GDP line (printed ink)
    "white": "#FFFFFF",      # page background, cards
    "navy": "#2B4B9B",       # deep series (electricity)
    "slate": "#555B63",      # secondary series
    "periwinkle": "#7E97D8",  # gridlines, light fills
    "ink_blue": "#1E3A8A",   # darkest ramp end
}

# Monochromatic blue ramp for multi-series charts (ports, vessel types).
BLUE_RAMP = ["#D4DCF2", "#A9BCE6", "#7E97D8", "#5276C6",
             "#3D5DAE", "#2B4B9B", "#1E3A8A", "#16295E"]

# Signal families: NTL mid-blue, electricity navy, ports slate-blue ramp,
# consumption deep navy, official GDP black.
SIGNAL = {
    "ntl": "#5276C6",
    "elec": "#2B4B9B",
    "mfg": "#555B63",
    "consumption": "#1E3A8A",
    "official": "#000000",
}


def plotly_sequence(n=8):
    """n distinguishable series colors from the blue ramp (cycled if needed)."""
    if n <= len(BLUE_RAMP):
        return BLUE_RAMP[:n]
    return [BLUE_RAMP[i % len(BLUE_RAMP)] for i in range(n)]


def apply_ryo(fig, height=420, legend=True):
    """Common layout: white plot, periwinkle grid, black text."""
    fig.update_layout(
        height=height,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="black"),
        xaxis=dict(gridcolor="#D4DCF2"),
        yaxis=dict(gridcolor="#D4DCF2"),
        legend_title_text="",
    )
    if not legend:
        fig.update_layout(showlegend=False)
    return fig


def callout(fig, x, y, text):
    """Yellow story box pinned to a data point. Text states facts + values."""
    fig.add_annotation(x=x, y=y, text=text, showarrow=True, arrowhead=2,
                       bgcolor=RYO["yellow"], font=dict(color="black", size=11))
    return fig
