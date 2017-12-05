from multiprocessing.pool import Pool

import matplotlib
import sys

matplotlib.use('GTK3Agg')
import pandas as pd
import matplotlib.pyplot as plt
import json
import os


class GSRun:
    data_dir = None

    def __init__(self, run_name, id):
        self.params = None
        self.df = None
        self.run_name = run_name
        self.id = id

    def __str__(self):
        return "{} - {}: {}".format(self.run_name, self.id, "Success" if self.is_success() else "Fail")

    def read_data(self):
        csv_path = "{}/{}-{}-stats.csv".format(GSRun.data_dir, self.run_name, self.id)
        json_path = "{}/{}-{}-params.json".format(GSRun.data_dir, self.run_name, self.id)

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


# Wrapper to allow pool.map to concurrently read CSVs
def csv_worker(run):
    # Speed up importing CSVs
    run.read_data()
    print(run)

    return run


def summarize_runs(runs):
    merged_runs = {}
    for name in get_run_names(runs):

        successful = get_successful_runs(runs, name)

        if len(successful) > 0:
            merged = pd.concat(map(lambda r: r.df, successful))
            summarized = merged.groupby('tick').mean()
            summarized.popCount = summarized.popCount.round()

            summarized["sharePercentStdUpper"] \
                = summarized.apply(lambda row: row['sharePercentAvg'] + row['sharePercentSD'], axis='columns')
            summarized["sharePercentStdLower"] \
                = summarized.apply(lambda row: row['sharePercentAvg'] - row['sharePercentSD'], axis='columns')

            merged_runs[name] = summarized

        else:
            merged_runs[name] = None

        # print("{}: {}".format(name, len(successful)))

    return merged_runs


def get_run_names(runs):
    return sorted(list(set(map(lambda x: x.run_name, runs))))


def get_successful_runs(runs, name):
    successful = list(filter(lambda r: r.run_name == name and r.is_success(), runs))
    # if max_runs is not None:
    #    successful = successful[:max_runs]

    return successful


def graph_pops(runs_dict, title):
    ax = None
    for name, df in sorted(runs_dict.items()):
        # print(df)
        if ax is None and df is not None:
            ax = df.plot(y="popCount", label=name, title=title)

        elif df is not None:
            df.plot(y="popCount", label=name, ax=ax)


def graph_sp(runs_dict, title):
    ax = None

    x = 0
    for name, df in sorted(runs_dict.items()):
        # print(df)
        if df is not None:
            df2 = df[["sharePercentMin", "sharePercentMax", "sharePercentStdLower", 'sharePercentStdUpper', 'sharePercentAvg']]
            if ax is None:
                ax = df2.plot(label="{} avg".format(name), title=title)
            else:
                df2.plot(label="{} avg".format(name), ax=ax)

            x = x + 1


def graph_sp_by_pop(runs_dict, title):
    ax = None
    for name, df in sorted(runs_dict.items()):
        # print(df)
        if df is not None:
            df2 = df.groupby('popCount').mean()

            if ax is None:
                ax = df2.plot(y="sharePercentAvg", label=name, title=title)
            else:
                df2.plot(y="sharePercentAvg", label=name, ax=ax)


def filter_runs(runs, names):
    return {key: runs[key] for key in runs.keys() if key in names}


def success_rates(runs):
    cols = ["run_name", "count", "successes", "success_rate"]
    vals = []
    for name in get_run_names(runs):
        run_count = len(list(filter(lambda r: r.run_name == name, runs)))
        run_success = len(get_successful_runs(runs, name))
        run_success_rate = run_success / run_count

        vals.append([name, run_count, run_success, run_success_rate])

    df = pd.DataFrame(vals, columns=cols)
    return df


def verify_params(runs):
    # Check to ensure that named runs all have the same params
    for name in get_run_names(runs):
        prev = None
        for run in list(filter(lambda r: r.run_name == name and r.is_success(), runs)):
            if prev is None:
                prev = run.params
            elif prev != run.params:
                print("ERROR MISMATCHED PARAMS: {}".format(run))
                sys.exit()


def graph_success(df, title):
    df.plot.bar(x='run_name', y='success_rate', title=title, color="Orange")


def main():
    data_dir = "/home/simon/Dropbox/School/TCSS 499/Data/test-group4/stats"

    GSRun.data_dir = data_dir

    # Read data from files
    all_files = []
    for file in sorted(os.listdir(data_dir)):
        if file.endswith(".csv"):
            filename_parts = file.split('-')
            run = GSRun(filename_parts[0], filename_parts[1])
            all_files.append(run)

    # concurrently read files
    pool = Pool(processes=6)
    all_runs = pool.map(csv_worker, all_files)
    pool.close()
    print("{} Runs".format(len(all_runs)))
    verify_params(all_runs)  # make sure we don't have any mixed names/params

    # Calculate Success Rates
    success_df = success_rates(all_runs)
    print(success_df)

    # Merge runs by name
    summarized_dict = summarize_runs(all_runs)

    # Get names of all public goods runs
    pg_runs = []
    for x in range(10):
        pg_runs.append("pg1{}".format(x))

    # Show Success & Counts
    pg_success = success_df[success_df['run_name'].isin(pg_runs)]
    pg_success = pg_success.append(success_df[success_df['run_name'].isin(["default"])])  # Add defaults at end
    graph_success(pg_success, "Success Rates of Runs")  # only show pg

    plt.tight_layout()
    plt.savefig('graphs/successes.pdf', format='pdf')

    # Compare Public Goods
    pg_runs.append("default")
    graph_pops(filter_runs(summarized_dict, pg_runs), "Mean Population of Public Goods Factors")
    plt.tight_layout()
    plt.savefig('graphs/pg-pop.pdf', format='pdf')
    graph_sp_by_pop(filter_runs(summarized_dict, pg_runs), "Mean Population vs Share Percent of Public Goods Factors")
    plt.tight_layout()
    plt.savefig('graphs/pg-popsp.pdf', format='pdf')

    # Compare Uniform vs Normal Forage
    # graph_pops(filter_runs(summarized_dict, ["default", "normalForage"]), "Mean Population of Foraging Methods")
    graph_sp_by_pop(filter_runs(summarized_dict,  ["default", "normalForage"]), "Mean Population vs Share Percent of Foraging Methods")
    plt.tight_layout()
    plt.savefig('graphs/foraging.pdf', format='pdf')
    # graph_sp(filter_runs(summarized_dict,  ["normalForage"]), "Share Percent of Normal Foraging")
    # graph_sp(filter_runs(summarized_dict,  ["default"]), "Share Percent of Uniform Foraging")

    # Compare Breed/Share
    sb_runs = ["sb8", "sb16", "sb32", "default"]
    graph_pops(filter_runs(summarized_dict, sb_runs), "Mean Population of Max Breed/Share")
    plt.tight_layout()
    plt.savefig('graphs/sb.pdf', format='pdf')
    # graph_sp_by_pop(filter_runs(summarized_dict, sb_runs), "Mean Population vs Share Percent of Max Breed/Share")

    # Compare Step
    step_runs = ["step4", "step8", "step16", "default"]
    graph_pops(filter_runs(summarized_dict, step_runs), "Mean Population of Mutation Steps")
    plt.tight_layout()
    plt.savefig('graphs/step.pdf', format='pdf')
    # graph_sp_by_pop(filter_runs(summarized_dict, step_runs), "Mean Population vs Share Percent of Mutation Steps")

    # Combined Runs
    # graph_sp(filter_runs(summarized_dict, {"default"}), "Mean Share Percent of Default Runs")
    # graph_sp_by_pop(filter_runs(summarized_dict, {"default"}), "Mean Population vs Mean Share Percent of Default Runs")

    plt.show()


if __name__ == "__main__":
    # execute only if run as a script
    main()
