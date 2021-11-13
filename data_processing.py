import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

pd.set_option("display.max_columns", None)
plt.rcParams["figure.figsize"] = (24, 12)


def getData():
    # get currently available data
    df = pd.read_csv(
        "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv",
        parse_dates=["date"],
    )

    # select attributes that we find interesting
    attributes = [
        "iso_code",
        "continent",
        "location",
        "date",
        "total_cases",
        "new_cases",
        "total_deaths",
        "new_deaths",
        "reproduction_rate",
        "icu_patients",
        "hosp_patients",
        "weekly_icu_admissions",
        "weekly_hosp_admissions",
        "new_tests",
        "total_tests",
        "positive_rate",
        "total_vaccinations",
        "people_vaccinated",
        "people_fully_vaccinated",
        "new_vaccinations",
        "stringency_index",
        "population",
        "population_density",
        "median_age",
        "aged_65_older",
        "aged_70_older",
        "gdp_per_capita",
        "extreme_poverty",
        "cardiovasc_death_rate",
        "diabetes_prevalence",
        "female_smokers",
        "male_smokers",
        "handwashing_facilities",
        "hospital_beds_per_thousand",
        "life_expectancy",
        "human_development_index",
        "excess_mortality",
    ]

    df = df[attributes]

    # let's store these rows which combine data of a continent in a seperate dataframe, so it doesn't give us any weird mistakes later/confuse us
    # before we do this we should be sure that really only these combined rows have NaNs
    # looking good, so lets create a new dataframe
    continent_df = df[df["continent"].isna()]
    # drop these rows from the original dataframe
    df = df[~df["continent"].isna()]

    # it seems that there are countries that don't have any values for new_cases or simply not enough values, these are obviously useless to us
    # lets drop all countries that have missing values for more than half of their entries for the column new_cases
    # (if they have more than half of the values, then we can fix the missing values with interpolation later)
    temp = (
        df[["location", "new_cases"]].groupby("location").count()["new_cases"]
        / df[["location", "new_cases"]].groupby("location").size()
    ) >= 0.5
    temp = temp[temp == True].index.tolist()
    # drop all rows that don't fulfill the above defined criteria
    df = df[df["location"].isin(temp)]
    # reset index, so that it is correct again (we dropped rows)
    df.reset_index(inplace=True, drop=True)

    # number of trailing NaNs for column new_cases
    temp = df.copy()
    temp.reset_index(inplace=True)
    last_index = temp.groupby("location").apply(lambda x: x.iloc[-1]["index"])
    last_valid_index = temp.groupby("location").apply(
        lambda x: x["new_cases"].last_valid_index()
    )

    # also while looking through the records, we found that some countries have leading NaNs for new_cases
    # let's remove these (while we're at it, let's also remove trailing NaNs)
    df = df.sort_values(by=["location", "date"]).reset_index(drop=True)
    # get the first and last valid index
    first_valid_index = df.groupby("location").apply(
        lambda x: x["new_cases"].first_valid_index()
    )
    last_valid_index = df.groupby("location").apply(
        lambda x: x["new_cases"].last_valid_index()
    )
    # create list of indices that we want to keep
    valid_indices = [
        np.arange(first, last + 1)
        for first, last in zip(first_valid_index, last_valid_index)
    ]
    # flatten it to be a 1D array instead of 2D
    valid_indices = [elem for sublist in valid_indices for elem in sublist]
    df = df[df.index.isin(valid_indices)]
    # we removed rows, so we need to reset the index
    df.reset_index(drop=True, inplace=True)

    # for some reason total_cases is complete, but new_cases isn't so let's fix that real quick
    miss_indices = df[df["new_cases"].isna()].index
    df.loc[miss_indices, "new_cases"] = list(
        df.iloc[miss_indices + 1]["total_cases"]
        - np.array(df.iloc[miss_indices]["total_cases"])
    )

    # also it seems that there are some columns where we simply have too many missing values for them to be useful, let's remove these
    cols_to_drop = [
        "icu_patients",
        "hosp_patients",
        "weekly_icu_admissions",
        "weekly_hosp_admissions",
        "excess_mortality",
    ]
    df.drop(columns=cols_to_drop, inplace=True)

    # maybe the high number of missing values comes from leading NaNs? let's check that (those are not the number of leading NaNs!!!!!!!)
    temp = df.copy()
    temp.reset_index(inplace=True)
    first_index = temp.groupby("location").apply(lambda x: x.iloc[0]["index"])
    first_valid_index = temp.groupby("location").apply(
        lambda x: x["total_vaccinations"].first_valid_index()
    )

    # so it seems that there are a lot of leading NaNs, however for some countries we don't have any vaccination numbers, lets remove these countries
    temp = first_valid_index - first_index
    # also after removing these countries, we need to reset the index (because we dropped some rows)
    df = df[~df["location"].isin(temp[temp.isna()].index)].reset_index(drop=True)

    # let's look at the first value of total_vaccinations for each country that isn't NaN
    first_valid_index = df.groupby("location").apply(
        lambda x: x["total_vaccinations"].first_valid_index()
    )

    # so unfortunately these aren't always zero, however just interpolating these leading NaNs would temper too much with the given data, so let's just set them to zero
    df.reset_index(inplace=True)
    first_index = df.groupby("location").apply(lambda x: x.iloc[0]["index"])
    df.drop(columns=["index"], inplace=True)
    # create list of indices that we want to change
    valid_indices = [
        np.arange(first, last - 1)
        for first, last in zip(first_index, first_valid_index)
    ]
    # flatten it to be a 1D array instead of 2D
    valid_indices = [elem for sublist in valid_indices for elem in sublist]
    # also set the people_vaccinated, people_fully_vaccinated, new_vaccinations to 0 for these rows
    df.loc[
        valid_indices,
        [
            "total_vaccinations",
            "people_vaccinated",
            "people_fully_vaccinated",
            "new_vaccinations",
        ],
    ] = 0

    # it's looking a lot better now, but the ~50% missing values for new_tests/total_tests are really annoying because these are such interesting columns
    # lets's check for leading NaNs
    temp = df.copy()
    temp.reset_index(inplace=True)
    # get the first index for each country
    first_index = temp.groupby("location").apply(lambda x: x.iloc[0]["index"])
    # get the first valid index for each country for the column total_tests
    first_valid_index = temp.groupby("location").apply(
        lambda x: x["total_tests"].first_valid_index()
    )

    # we can't do anything here as well..
    # so let's do some interpolation (we'll only interpolate between the first valid value and the last, because it would probably temper too much with the data)
    # first we'll look at the percentage of missing values for each column again
    cols = df.columns

    # since we're only gonna interpolate between the first and last valid value for each country, we can basically put each column in here and see to what extent it fixes something
    # we'll only interpolate the total_columns and add the missing values later for the new_columns
    cols_to_interpolate = [
        "total_deaths",
        "reproduction_rate",
        "total_tests",
        "positive_rate",
        "total_vaccinations",
        "people_vaccinated",
        "people_fully_vaccinated",
        "stringency_index",
        "population_density",
        "median_age",
        "aged_65_older",
        "aged_70_older",
        "gdp_per_capita",
        "extreme_poverty",
        "cardiovasc_death_rate",
        "diabetes_prevalence",
        "female_smokers",
        "male_smokers",
        "handwashing_facilities",
        "hospital_beds_per_thousand",
        "life_expectancy",
        "human_development_index",
    ]
    df = df.groupby("location").apply(
        lambda x: x[df.columns.difference(cols_to_interpolate)].join(
            x[cols_to_interpolate].interpolate(
                method="linear", axis=0, limit_area="inside"
            )
        )
    )[cols]
    # let's change new_deaths, new_tests and new_vaccinations accordingly now
    df[["new_deaths", "new_tests", "new_vaccinations"]] = (
        df.groupby("location")
        .apply(
            lambda x: x[["total_deaths", "total_tests", "total_vaccinations"]].diff()
        )
        .to_numpy()
    )

    # it might be fine to use the average value of the continent for a country for a specific column if it's completly missing
    # (this only applies to some columns (columns that describe local factors and that we won't expect to change much over the time interval))
    # however we should probably first look at the standard deviation and compare it with the mean and if the std is too big, we can't do it for that column
    cols_to_consider = [
        "location",
        "population_density",
        "median_age",
        "aged_65_older",
        "aged_70_older",
        "extreme_poverty",
        "cardiovasc_death_rate",
        "diabetes_prevalence",
        "female_smokers",
        "male_smokers",
        "handwashing_facilities",
        "hospital_beds_per_thousand",
        "life_expectancy",
        "human_development_index",
    ]
    # get the continent for each country
    continents = df.groupby("location").apply(lambda x: x.iloc[0]["continent"])
    # get the mean value for the considered columns for each country
    temp = df[cols_to_consider].groupby("location").mean()
    # add continent as column
    temp["continent"] = continents
    # now get the relative size of std to mean for each continent and then average that out for all continents
    means = temp.groupby("continent").mean()
    means_all = (
        temp.groupby("continent").std() / temp.groupby("continent").mean()
    ).mean()

    # for some columns the std is quite big compared to the mean value, for these columns it's probably not a good idea to just use the mean
    # now we just need to define a threshhold at which we want to use the mean of the continent for missing values
    threshhold = 0.5
    cols_to_use_mean = means_all <= threshhold
    cols_to_use_mean = cols_to_use_mean[cols_to_use_mean].index

    for col in cols_to_use_mean:
        # get all rows that are NaN for this column
        nan_indices = df[col].isna()
        # set it to the mean value of the continent of that country for that column
        df.loc[nan_indices, col] = means.loc[
            df[nan_indices]["continent"], col
        ].to_numpy()

    return df