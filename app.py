import pandas as pd
import plotly.express as px
import streamlit as st
from utils.data import load

st.set_page_config(page_title="What is the best time to consume electricity?", layout="wide")

#Downloading the data and using a cache to avoid downloading it again every time.
@st.cache_data(show_spinner="Downloading data")
def get_data():
    return load()

df, quality = get_data()

#Filters:
with st.sidebar:
    st.header("Filters")
    a_min, a_max = int(df["year"].min()), int(df["year"].max())
    years = st.slider("Years", a_min, a_max, (max(a_min, a_max - 5), a_max))
    seasons = st.multiselect("Seasons", ["Winter", "Spring", "Summer", "Autumn"], default=["Winter", "Spring", "Summer", "Autumn"])
    days = st.radio("Days", ["All", "Weekday", "Weekend"])

# Filtering the data based on the selected filters.
d = df[df["year"].between(*years) & df["season"].isin(seasons)]
if days == "Weekday":
    d = d[~d["weekend"]]
elif days == "Weekend":
    d = d[d["weekend"]]
if d.empty:
    st.warning("No data found with these filters.")
    st.stop()

# Average CO2 for each hour
profil = d.groupby("hour")["taux_co2"].mean()  
clean_hour, polluting_hour = int(profil.idxmin()), int(profil.idxmax())


st.title("At what time of day is electricity the cleanest in France?")
st.markdown(
    "In France, thanks to a number of nuclear power plants, electricity is already quite low in carbon emissions. " \
    "However, its cleanliness varies throughout the day. /n"
    "At peak hours when everyone is using electricity mostly for personnal use (cooking, watching TV. ect...), Electric companies have to turn on gas or coal power plants to meet the demand. "
    "As a result, you normal use of electricity can emit significantly more or less CO2 depending on the time of day."
)

#Setting up the metrics to display the average CO2, the cleanest hour, the most polluting hour, and the spread between them with profil.min and max giving an idea of CO2 at that time.
c1, c2, c3, c4 = st.columns(4)
c1.metric("average CO2", f"{d['taux_co2'].mean():.0f} g/kWh")
c2.metric("Cleanest hour", f"{clean_hour} h", f"{profil.min():.0f} g/kWh")
c3.metric("Most Polluting hour", f"{polluting_hour} h", f"{profil.max():.0f} g/kWh",delta_color="inverse")
c4.metric("Spread", f"× {profil.max() / profil.min():.1f}")

#Graph 1: Heat map
st.header("1. The use of polluting electricity changes depending on the time of day but more importantly the month of the year.")
map = d.pivot_table(index="hour", columns="month", values="taux_co2", aggfunc="mean")
fig = px.imshow(map, aspect="auto", color_continuous_scale="RdYlGn_r", labels=dict(x="Month", y="Hour of the day", color="g CO2/kWh"))
st.plotly_chart(fig, use_container_width=True)
st.caption("This heat map shows the CO2 intensity of electricity use across hours and months. " \
"Red indicates more carbon intensive electricity (such as evenings in January which makes sense since more electricity is used to warm houses), " \
"while green indicates cleaner electricity (for example,nights and afternoons during summer where the wind does the job of cooling the hous saving in the process electricity).")

#Graph 2 : CO2 over time depending on the season.
st.header("2. Each season has its own typical days with hours generaly being cleaner or more polluting than others.")
for_each_season = d.groupby(["season", "hour"], as_index=False)["taux_co2"].mean()
fig = px.line(for_each_season, x="hour", y="taux_co2", facet_col="season", facet_col_wrap=2, labels={"hour": "Hour", "taux_co2": "g CO2/kWh"}, height=550)
st.plotly_chart(fig, use_container_width=True)
st.caption("As such we can see that winter is much more polluting than other seasons with summer and spring being the cleanest, " \
"furthermore we can observe a trend on all seasons that CO2 emissions peak around 8h and 20h which corresponds to the time people leave and come home. ")

#Graph 3: Evolution across time
st.header("3. How about in the long run ?")
per_year = df.groupby("year", as_index=False)["taux_co2"].mean()
fig = px.line(per_year, x="year", y="taux_co2", markers=True, labels={"year": "Year", "taux_co2": "g CO2/kWh (average)"})
fig.add_hline(y=df["taux_co2"].mean(), line_dash="dot", annotation_text="Average across all years")
st.plotly_chart(fig, use_container_width=True)
st.caption("We can see as a matter of fact that the average CO2 emissions of electricity in France has been decreasing over the years, " \
"this is due to the fact that more and more renewable energy sources are being used to produce electricity. " \
"However, we can also see that there are some years where the average CO2 emissions are higher than others, " \
"this is due to the fact that some years have more extreme weather, a pandemic and other factors. " \
"This not only gives us a good idea of the future but is also a testment to the past and how we use electricity in dire times.")

#Graph 4: Impact of changing habits sliders
st.header("4. How much CO2 can you save by changing your habits ?")
DEVICE = {"Washing machine (1 kWh)": 1.0, "Dishwasher (1,2 kWh)": 1.2, "Water heater (3 kWh)": 3.0, "Electric car charging (10 kWh)": 10.0}
a, b, c = st.columns(3)
name = a.selectbox("Device", list(DEVICE))
usual_hour = b.slider("I normally use it at", 0, 23, 19, format="%d h")
times = c.slider("Number of times per week", 1, 14, 3)

kwh = DEVICE[name]
gain_g = kwh * (profil[usual_hour] - profil.min())
gain_kg_an = gain_g * times * 52 / 1000
st.markdown(
    f"By using it at **{clean_hour} h** instead of **{usual_hour} h**, "
    f"you avoid consuming approximately **{gain_kg_an:.1f} kg of CO2 per year**."
)

#DATA Quality
st.header("How good is the data and what are its limitations ?")
q1, q2, q3, q4 = st.columns(4)
q1.metric("Ligns in the dataset", f"{quality['ligns']:,}".replace(",", " "))
q2.metric("Missing CO2 values", quality["missing_co2"])
q3.metric("Duplicates", quality["duplicates"])
q4.metric("Weird values", quality["weird_values"])
st.markdown(
    "Limitations :/n "
    "1. We are using the average CO2 emissions which differ slightly from the actual CO2 emissions ; "
    "2. If everyone shifts their consumption to the same time, the curve would only shift but wont change therefore bringing us back to square one ; "
    "3. The data is national, without regional differences so depending where you live, the results may vary ; "
    "4. This does not prove anything and all claims made are only asumptions and deductions made from looking at the data."
)

# Conclusion
st.header("What are the key takeaways ?")
st.markdown(
    "- Pluging in your laptop or turning on the washing machine during certain hours can greatly help reduce your carbon footprint without affecting your daily routine.\n"
    "- The right time also depends on the season, you can use the heat map as a general guide but winter usually reauires more energy for heating and is therefore more poluting.\n"
    "- The day of the month doesn't appear to have a significant impact.\n"
    "- The development of renewable energy sources is helping reduce emissions.\n"
    "- Events happening in the world can influence electricity consumption patterns.\n"
    "- The data is not perfect and should be taken with a grain of salt furthermore if every body changes their habits to the same time the problem will stay the same.\n"
)
st.caption("Source : RTE, éCO₂mix national – data.gouv.fr / ODRÉ https://odre.opendatasoft.com/explore/dataset/eco2mix-national-cons-def/")
