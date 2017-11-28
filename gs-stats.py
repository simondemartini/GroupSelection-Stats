import pandas as pd
import matplotlib.pyplot as plt
import json
import os


class GSRun:
    def __init__(self, run_name, id):
        self.params = None
        self.df = None
        self.run_name = run_name
        self.id = id

    def __str__(self):
        return "{} - {}: {}".format(self.run_name, self.id, "Success" if self.is_success() else "Fail")

    def read_data(self, src_dir):
        csv_path = "{}/{}-{}-stats.csv".format(src_dir, self.run_name, self.id)
        json_path = "{}/{}-{}-params.json".format(src_dir, self.run_name, self.id)

        self.df = pd.read_csv(csv_path)
        # print(self.df.dtypes)

        with open(json_path) as params_file:
            self.params = json.load(params_file)
            # print(self.params)

        return "FILES: {} {}".format(csv_path, json_path)

    def is_success(self):
        last_day = self.df.tick.max()
        max_day = self.params['maxDays'] - 1
        return last_day >= max_day


def summarize_runs(runs):
    merged_runs = {}
    for name in get_run_names(runs):
        successful = list(filter(lambda r: r.run_name == name and r.is_success(), runs))
        if len(successful) > 0:
            merged = pd.concat(map(lambda r: r.df, successful))
            summarized = merged.groupby('tick').mean()

            merged_runs[name] = summarized

        else:
            merged_runs[name] = None

        print("{}: {}".format(name, len(successful)))

    return merged_runs


def get_run_names(runs):
    return sorted(list(set(map(lambda x: x.run_name, runs))))


def main():
    data_dir = "/home/simon/Dropbox/School/TCSS 499/Data/test-group4/stats"

    all_runs = []
    for file in sorted(os.listdir(data_dir)):
        if file.endswith(".csv"):
            filename_parts = file.split('-')
            run = GSRun(filename_parts[0], filename_parts[1])
            run.read_data(data_dir)
            all_runs.append(run)
            print(run)

    print(len(all_runs))
    ax = None
    for name, df in summarize_runs(all_runs).items():
        # print(df)
        if ax is None and df is not None:
            ax = df.plot(y="popCount", label=name, title="Population Count vs Time")

        elif df is not None:
            df.plot(y="popCount", label=name, ax=ax)

    plt.show()


if __name__ == "__main__":
    # execute only if run as a script
    main()
