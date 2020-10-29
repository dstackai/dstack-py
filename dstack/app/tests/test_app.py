from unittest import TestCase


class TestApp(TestCase):
    def test_first_example(self):
        pass
        # import pandas as pd
        # from datetime import date, timedelta
        #
        # @depends(project=True)  # required a whole project to be compiled
        # def covid_cases(country: str, weeks: int):
        #     def get_fig(observed_data: pd.DataFrame, result: PredictionResults) -> Figure:
        #         # create combined plot
        #         pass
        #
        #     today = date.today()
        #     observed = pull(f"covid/observed")
        #     model = pull(f"covid/cases_predictor/{country}")
        #     prediction = model.get_prediction(start=today, end=today + timedelta(weeks=weeks), dynamic=False)
        #     return get_fig(observed, prediction)
        #
        # def int_validator(value: str) -> int:
        #     return int(value)
        #
        # class Country:
        #     name: str
        #     ...
        #
        # def load_countries() -> List[Country]:
        #     pass
        #
        # push("my_project/my_app", covid_cases, description="My first NLP model",
        #      country=ComboBox(label="Your text", data=load_countries, model=lambda x: x.name),
        #      weeks=TextField(label="Number of weeks", validator=int_validator))
