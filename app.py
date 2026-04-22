import traceback
import io
import base64
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import numpy as np
from flask import Flask, render_template, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return e
    return f"<h3>Wait! An Internal Server Error occurred!</h3><br><b>Here's the technical error to copy/paste to me:</b><br><br><pre>{traceback.format_exc()}</pre>", 500

# ─── Base configuration ────────────────────────────────────────────────────────
BASE_TIME = 30  # Base delivery time in minutes

# Additive penalty/bonus lookup tables
WEATHER_FACTORS = {
    "clear":     0,
    "cloudy":    3,
    "rainy":     10,
    "stormy":    20,
    "foggy":     8,
}

VEHICLE_FACTORS = {
    "bicycle":   8,
    "motorcycle": 0,
    "scooter":   2,
    "car":       5,   # car can be slower in traffic
    "electric_bike": 1,
}

TRAFFIC_FACTORS = {
    "low":       -5,
    "medium":    0,
    "high":      10,
    "jam":       20,
}

CITY_FACTORS = {
    "urban":        0,
    "metropolitan": 8,   # larger city = slightly longer due to complexity
    "suburban":    -3,
    "rural":       -5,
}

FESTIVAL_FACTOR = 15   # extra minutes added during festivals

# ─── Helper: generate the comparison chart ─────────────────────────────────────
def generate_chart(normal_time: float, festival_time: float) -> str:
    """Generate a bar chart comparing normal vs festival avg delivery time.
    Returns a base64-encoded PNG string."""

    categories = ["Normal Day", "Festival Day"]
    values     = [normal_time, festival_time]
    colors     = ["#EF4F5F", "#FF8C42"]

    fig, ax = plt.subplots(figsize=(6, 4))
    fig.patch.set_facecolor("#1a1a1a")
    ax.set_facecolor("#1a1a1a")

    bars = ax.bar(categories, values, color=colors, width=0.45,
                  edgecolor="none", zorder=3)

    # Value labels on bars
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.8,
            f"{val:.0f} min",
            ha="center", va="bottom",
            color="#ffffff", fontsize=12, fontweight="bold"
        )

    # Difference annotation
    diff = festival_time - normal_time
    ax.annotate(
        f"+{diff:.0f} min on festivals",
        xy=(1, festival_time),
        xytext=(0.5, festival_time + 10),
        fontsize=10, color="#FF8C42",
        ha="center",
        arrowprops=dict(arrowstyle="->", color="#FF8C42", lw=1.5),
    )

    ax.set_ylim(0, max(values) + 30)
    ax.set_ylabel("Avg Delivery Time (min)", color="#a0a0a0", fontsize=11)
    ax.set_title("Festival vs Normal Day Delivery Time", color="#ffffff",
                 fontsize=13, fontweight="bold", pad=12)

    ax.tick_params(colors="#a0a0a0")
    ax.spines[:].set_color("none")
    ax.yaxis.grid(True, color="#2e2e2e", linestyle="--", zorder=0)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    return encoded


# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
@app.route("/delivery-time-predictor")
def home():
    return render_template(
        "index.html",
        prediction_text=None,
        chart_data=None,
        weather_options=list(WEATHER_FACTORS.keys()),
        vehicle_options=list(VEHICLE_FACTORS.keys()),
        traffic_options=list(TRAFFIC_FACTORS.keys()),
        city_options=list(CITY_FACTORS.keys()),
    )


@app.route("/predict", methods=["POST"])
def predict():
    try:
        # ── Collect inputs ──────────────────────────────────────────────────
        rating     = float(request.form["rating"])
        rating     = min(rating, 5.0)
        distance   = float(request.form["distance"])
        weather    = request.form.get("weather", "clear")
        vehicle    = request.form.get("vehicle", "motorcycle")
        traffic    = request.form.get("traffic", "medium")
        city       = request.form.get("city", "urban")
        is_festival = request.form.get("festival") == "yes"

        # ── Factor lookup (default to 0 if unknown) ─────────────────────────
        weather_add  = WEATHER_FACTORS.get(weather, 0)
        vehicle_add  = VEHICLE_FACTORS.get(vehicle, 0)
        traffic_add  = TRAFFIC_FACTORS.get(traffic, 0)
        city_add     = CITY_FACTORS.get(city, 0)
        festival_add = FESTIVAL_FACTOR if is_festival else 0

        DISTANCE_FACTOR = 5
        RATING_FACTOR   = 2

        # ── Prediction formula ──────────────────────────────────────────────
        predicted_time = (
            BASE_TIME
            + (DISTANCE_FACTOR * distance)
            - (RATING_FACTOR * rating)
            + weather_add
            + vehicle_add
            + traffic_add
            + city_add
            + festival_add
        )
        predicted_time = max(predicted_time, 5)   # at least 5 minutes

        # Normal-day time (same inputs but no festival penalty)
        normal_time  = predicted_time - festival_add
        festival_time = normal_time + FESTIVAL_FACTOR

        # ── Format output ───────────────────────────────────────────────────
        def fmt_time(mins):
            mins = int(round(max(mins, 0)))
            if mins >= 60:
                return f"{mins // 60}hr+{mins % 60} mins"
            return f"{mins} mins"

        time_str = fmt_time(predicted_time)
        label_prefix = "🎉 Festival Day" if is_festival else "📅 Normal Day"

        # ── Chart ───────────────────────────────────────────────────────────
        chart_data = generate_chart(normal_time, festival_time)

        return render_template(
            "index.html",
            prediction_text=f"{label_prefix} — Estimated Delivery: {time_str}",
            chart_data=chart_data,
            chart_normal=f"{normal_time:.0f}",
            chart_festival=f"{festival_time:.0f}",
            # Re-populate dropdowns
            weather_options=list(WEATHER_FACTORS.keys()),
            vehicle_options=list(VEHICLE_FACTORS.keys()),
            traffic_options=list(TRAFFIC_FACTORS.keys()),
            city_options=list(CITY_FACTORS.keys()),
            sel_weather=weather,
            sel_vehicle=vehicle,
            sel_traffic=traffic,
            sel_city=city,
            sel_rating=rating,
            sel_distance=distance,
            sel_festival="yes" if is_festival else "no",
        )

    except Exception:
        return render_template(
            "index.html",
            prediction_text="❌ Invalid input — please check your values.",
            chart_data=None,
            weather_options=list(WEATHER_FACTORS.keys()),
            vehicle_options=list(VEHICLE_FACTORS.keys()),
            traffic_options=list(TRAFFIC_FACTORS.keys()),
            city_options=list(CITY_FACTORS.keys()),
        )


if __name__ == "__main__":
    app.run(debug=True)