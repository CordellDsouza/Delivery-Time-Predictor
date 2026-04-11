from flask import Flask, render_template, request

app = Flask(__name__)

# Base average delivery time (you can adjust this)
avg_time = 30  

@app.route("/")
@app.route("/delivery-time-predictor")
def home():
    return render_template("index.html", prediction_text=None)

@app.route("/predict", methods=["POST"])
def predict():
    try:
        rating = float(request.form["rating"])
        if rating > 5.0:
            rating = 5.0
        distance = float(request.form["distance"])

        # Logic-based prediction
        distance_factor = 5
        rating_factor = 2

        predicted_time = (
            avg_time
            + (distance_factor * distance)
            - (rating_factor * rating)
        )

        predicted_mins = int(round(predicted_time))
        if predicted_mins >= 60:
            hrs = predicted_mins // 60
            mins = predicted_mins % 60
            time_str = f"{hrs} hr {mins} mins"
        else:
            time_str = f"{predicted_mins} mins"

        return render_template(
            "index.html",
            prediction_text=f"Estimated Delivery Time: {time_str}"
        )

    except:
        return render_template(
            "index.html",
            prediction_text="Invalid input"
        )

if __name__ == "__main__":
    app.run(debug=True)