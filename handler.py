from main import (
    executeSql,
    get_hr_data
)


def getOutput(question: str):

    print("GET HR OUTPUT START")

    master_df, work_experience_df = get_hr_data()

    print("Master rows:", len(master_df))
    print("Work experience rows:", len(work_experience_df))

    response = executeSql(
        question,
        master_df,
        work_experience_df
    )

    print("GET HR OUTPUT END")

    return response