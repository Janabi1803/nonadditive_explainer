import os
import time
import pandas as pd
import numpy as np
import pickle
import matplotlib.pyplot as plt
from sklearn import set_config
from sksurv.linear_model import CoxPHSurvivalAnalysis
os.chdir('/Users/abdallah/Desktop/Kings College Project/Code/GIT_Repo')
from survshap.survshap import *
from survshap.survlime import *
from explainer import *
import surv_utils
from sksurv.preprocessing import OneHotEncoder
from sksurv.ensemble import RandomSurvivalForest
from nonadditive_explainers import nonadditive_explainer









    # load the relevant data
os.chdir('/Users/abdallah/Desktop/Kings College Project/Code/Data prepation ELSA Dementia/DATA/')
with open('/Users/abdallah/Desktop/Kings College Project/Code/Data prepation ELSA Dementia/DATA/cat_feature_dict.pkl', 'rb') as fp:
    cat_feature_dict = pickle.load(fp)
data_w1_dummied = pd.read_csv("/Users/abdallah/Desktop/Kings College Project/Code/Data prepation ELSA Dementia/DATA/data_w1_dummied.csv", index_col=0)
data_w1_dummied_unstandardised = pd.read_csv("/Users/abdallah/Desktop/Kings College Project/Code/Data prepation ELSA Dementia/DATA/data_w1_dummied_unstandardised.csv", index_col=0)
variable_definitions = pd.read_csv("/Users/abdallah/Desktop/Kings College Project/Code/Data prepation ELSA Dementia/DATA/variable_definitions.csv", index_col=0)
data_w1 = pd.read_csv("/Users/abdallah/Desktop/Kings College Project/Code/Data prepation ELSA Dementia/DATA/data_w1.csv", index_col=0)
#TODO put that in the preprocessing file


    # feature aggregation of predictors indicating social participation 
data_w1_dummied["social"] = data_w1_dummied[['scorg1', 'scorga2', 'scorg4', 'scorg5', 'scorg6', 'scorg7', 'scorg8']].sum(axis=1)

# Features to include according to literature:
    # age, sex and race  , grip-strength, number of chronic diseases and depressive symptoms
    # educational degree, increased age, being female and absent religious status 
    # neuropsychiatric symptoms, cognitive engagement
selected_features = ['scorg3', 'social',
                         "cesd_sc",'n_chronic_diseases',"n_neuropsychiatric_symptoms",
                          'ethnicity_White', 'gender_Men', 'mmgsd_w2', 
                        'edqual_Degree or equiv', 'edqual_Foreign/other',
                        'edqual_NVQ/GCE O/A Level equiv', 'edqual_No qualification', 
                         'memory1', 'procspeed1', # left out 'exe1',  as it correlates strongly (0.46) with memory1 and is a similar construct
                          "age", "dem_hse_w8", "time"]
    # the categorical features of the selected features
categ_features = [ 'scorg3','social',
                          'ethnicity_White', 'gender_Men', 
                        'edqual_Degree or equiv', 'edqual_Foreign/other',
                        'edqual_NVQ/GCE O/A Level equiv', 'edqual_No qualification', 
                          ]
    # random seed
random_state=1
    # use 100 instances for testing, the rest for training
test_indices = data_w1_dummied.sample(100, random_state=random_state).index
training_indices = [x for x in data_w1_dummied.index if x not in test_indices]
training = data_w1_dummied.loc[training_indices, selected_features]
test = data_w1_dummied.loc[test_indices, selected_features]

    # Split into predictors and targets
training_x, training_y = surv_utils.convert_time_y_to_surv_y(df = training, y = "time", event_indicator = "dem_hse_w8", only_targets = False, round_y= False) 
test_x, test_y = surv_utils.convert_time_y_to_surv_y(df = test, y = "time", event_indicator = "dem_hse_w8", only_targets = False, round_y= False)

    # Fit a survival model that we will try to explain: a RSF
rsf = RandomSurvivalForest(
    n_estimators=1000, min_samples_split=10, min_samples_leaf=15, n_jobs=-1, random_state=1
)
rsf.fit(training_x, training_y)


    # initialise explanations and timer dictionaries to save results
explanations=dict()
explanations["survMLeX"] = []
explanations["survLIME"] = []
explanations["survSHAP"] = []
explanations["survChoquEx"] = []
timer=dict()
timer["survMLeX"] = []
timer["survLIME"] = []
timer["survSHAP"] = [] 
timer["survChoquEx"] = []

    # initialise counter at 0
counter=0

    # TODO check which hyperparameter settings are the most promising for the survMLeX
    # Fit the explainer 
explainer_fidelity = ExplainSurvival(
                        model = rsf, # the model whose output we want to explain 
                        x = training_x, # DUMMIED data that was used to train the blackbox model
                        y = training_y, # the outcome data in a format suitable for sklearn survival models  
                        categorical_features = categ_features, # List of strings of the feature labels corresponding to categorical features
                        random_state = random_state, # random state for intilisation of random functions
                        )

    # Get global measures of feature importance
explainer_fidelity.global_feature_importance() #TODO check if this works



for instance_id in test_x.index:
    instance = np.array(test_x.loc[instance_id, :])

    # calculate the explanations for the survMLeX method 
    st = time.time()
    explanationSurvMLeX = explainer_fidelity.explain_instance( 
                        instance = instance , # Pass instance as a np.array or pd.series                         
                        method = "SurvMLeX", # Explanation method: either "SurvMLeX", "SurvChoquEx", "SurvLIME" or "SurvSHAP"
                        binary=False, # Using a binary representation for the perturbed samples. Default is False
                        aggregation_method = "percentile", # How to aggregate survival function predictions to a time-to-event estimate: "trapezoid", "median" or "percentile"
                        threshold_aggregation = 0.7, # Which threshold to use when aggregating survival curves to a time-to-event estimate using the percentile method (if it is not finetuned)
                        find_best_cutoff = False, # Finds optimal value for threshold_blackbox_clf argument
                        n_perturbed=1400, # Size of the perturbed dataset
                        weighing_multiplier = 1.5, # How much larger the perturbed dataset will be after weighing through sampling with replacement  
                        finetune_explainer=True, # Whether to finetune expainer (only for SurvMLeX, SurvChoquEx and SurvSHAP)
                        only_shapley_values=True, # Not relevant if method="SurvLIME". For other methods it wont use identified features to fit a Cox regression model but give the shapley values right away
                        k_features=10, # The number of features to retain if a penalised Cox regression is fit (only if only_shapley_values=False)
                        plot_curve=False, # Whether explainer should also plot survival curve (only if only_shapley_values=False)
                        alpha_min_ratio=0.01, # alpha_min_ratio argument for the penalised Cox regression (only if only_shapley_values=False)
                        alpha=1.0, # Alpha parameter of SurvMLeX or SurvChoquEx
                        survshap_calculation_method="sampling" # for survshap method: can be either "kernel", "sampling", "treeshap" or "shap_kernel"
                        ) 
    explanations["survMLeX"].append(explanationSurvMLeX["shapley_values"]["feature_names"])
    et = time.time()
    elapsed_time = et - st # print('Execution time:', elapsed_time, 'seconds')
    timer["survMLeX"].append(elapsed_time)
    print("survMLeX explanation: ", list(explanationSurvMLeX["shapley_values"]["feature_names"]))
    print("survMLeX needed", elapsed_time, "seconds.\n")

    # calculate the explanations for the ChoquEx method 
    st = time.time()
    explanationChoquEx = explainer_fidelity.explain_instance( 
                        instance = instance , # Pass instance as a np.array or pd.series                         
                        method = "SurvChoquEx", # Explanation method: either "SurvMLeX", "SurvChoquEx", "SurvLIME" or "SurvSHAP"
                        binary=False, # Using a binary representation for the perturbed samples. Default is False
                        aggregation_method = "percentile", # How to aggregate survival function predictions to a time-to-event estimate: "trapezoid", "median" or "percentile"
                        threshold_aggregation = 0.7, # Which threshold to use when aggregating survival curves to a time-to-event estimate using the percentile method (if it is not finetuned)
                        find_best_cutoff = False, # Finds optimal value for threshold_blackbox_clf argument
                        n_perturbed=1400, # Size of the perturbed dataset
                        weighing_multiplier = 1.5, # How much larger the perturbed dataset will be after weighing through sampling with replacement  
                        finetune_explainer=True, # Whether to finetune expainer (only for SurvMLeX, SurvChoquEx and SurvSHAP)
                        only_shapley_values=True, # Not relevant if method="SurvLIME". For other methods it wont use identified features to fit a Cox regression model but give the shapley values right away
                        k_features=10, # The number of features to retain if a penalised Cox regression is fit (only if only_shapley_values=False)
                        plot_curve=False, # Whether explainer should also plot survival curve (only if only_shapley_values=False)
                        alpha_min_ratio=0.01, # alpha_min_ratio argument for the penalised Cox regression (only if only_shapley_values=False)
                        alpha=1.0, # Alpha parameter of SurvMLeX or SurvChoquEx
                        survshap_calculation_method="sampling" # for survshap method: can be either "kernel", "sampling", "treeshap" or "shap_kernel"
                        ) 
    explanations["survChoquEx"].append(explanationChoquEx["shapley_values"]["feature_names"])
    et = time.time()
    elapsed_time = et - st # print('Execution time:', elapsed_time, 'seconds')
    timer["survChoquEx"].append(elapsed_time)
    print("survChoquEx explanation: ", list(explanationChoquEx["shapley_values"]["feature_names"]))
    print("survChoquEx needed", elapsed_time, "seconds.\n")


    # calculate the explanations for SurvLIME 
    st = time.time()
    explanationLIME = explainer_fidelity.explain_instance( 
                        instance = instance , # Pass instance as a np.array or pd.series                         
                        method = "SurvLIME", # Explanation method: either "SurvMLeX", "SurvChoquEx", "SurvLIME" or "SurvSHAP"
                        binary=False, # Using a binary representation for the perturbed samples. Default is False
                        aggregation_method = "percentile", # How to aggregate survival function predictions to a time-to-event estimate: "trapezoid", "median" or "percentile"
                        threshold_aggregation = 0.7, # Which threshold to use when aggregating survival curves to a time-to-event estimate using the percentile method (if it is not finetuned)
                        find_best_cutoff = False, # Finds optimal value for threshold_blackbox_clf argument
                        n_perturbed=1400, # Size of the perturbed dataset
                        weighing_multiplier = 1.5, # How much larger the perturbed dataset will be after weighing through sampling with replacement  
                        finetune_explainer=True, # Whether to finetune expainer (only for SurvMLeX, SurvChoquEx and SurvSHAP)
                        only_shapley_values=False, # Not relevant if method="SurvLIME". For other methods it wont use identified features to fit a Cox regression model but give the shapley values right away
                        k_features=10, # The number of features to retain if a penalised Cox regression is fit (only if only_shapley_values=False)
                        plot_curve=False, # Whether explainer should also plot survival curve (only if only_shapley_values=False)
                        alpha_min_ratio=0.01, # alpha_min_ratio argument for the penalised Cox regression (only if only_shapley_values=False)
                        alpha=1.0, # Alpha parameter of SurvMLeX or SurvChoquEx
                        survshap_calculation_method="sampling" # for survshap method: can be either "kernel", "sampling", "treeshap" or "shap_kernel"
                        ) 
    explanations["survLIME"].append(explanationLIME["hazard_ratios"])
    et = time.time()
    elapsed_time = et - st # print('Execution time:', elapsed_time, 'seconds')
    print("survLIME needed", elapsed_time, "seconds.\n")
    timer["survLIME"].append(elapsed_time)

    # Calculate the explanations for SurvSHAP
    st = time.time()
    explanationSHAP = explainer_fidelity.explain_instance( 
                        instance = instance , # Pass instance as a np.array or pd.series                         
                        method = "SurvSHAP", # Explanation method: either "SurvMLeX", "SurvChoquEx", "SurvLIME" or "SurvSHAP"
                        binary=False, # Using a binary representation for the perturbed samples. Default is False
                        aggregation_method = "percentile", # How to aggregate survival function predictions to a time-to-event estimate: "trapezoid", "median" or "percentile"
                        threshold_aggregation = 0.7, # Which threshold to use when aggregating survival curves to a time-to-event estimate using the percentile method (if it is not finetuned)
                        find_best_cutoff = False, # Finds optimal value for threshold_blackbox_clf argument
                        n_perturbed=1400, # Size of the perturbed dataset
                        weighing_multiplier = 1.5, # How much larger the perturbed dataset will be after weighing through sampling with replacement  
                        finetune_explainer=True, # Whether to finetune expainer (only for SurvMLeX, SurvChoquEx and SurvSHAP)
                        only_shapley_values=True, # Not relevant if method="SurvLIME". For other methods it wont use identified features to fit a Cox regression model but give the shapley values right away
                        k_features=10, # The number of features to retain if a penalised Cox regression is fit (only if only_shapley_values=False)
                        plot_curve=False, # Whether explainer should also plot survival curve (only if only_shapley_values=False)
                        alpha_min_ratio=0.01, # alpha_min_ratio argument for the penalised Cox regression (only if only_shapley_values=False)
                        alpha=1.0, # Alpha parameter of SurvMLeX or SurvChoquEx
                        survshap_calculation_method="sampling" # for survshap method: can be either "kernel", "sampling", "treeshap" or "shap_kernel"
                        ) 
    explanations["survSHAP"].append(explanationSHAP["shapley_values"]["feature_names"])
    et = time.time()
    elapsed_time = et - st # print('Execution time:', elapsed_time, 'seconds')
    timer["survSHAP"].append(elapsed_time)
    print("survSHAP needed", elapsed_time, "seconds.\n")
    print("counter: ", counter, " instances explained.\n\n\n")    
    counter +=1




# Transform results

explanations_old = explanations.copy()

for i in np.arange(0,100):
    explanations["survChoquEx"][i] = list(explanations["survChoquEx"][i]["feature_names"])
    explanations["survMLeX"][i] = list(explanations["survMLeX"][i]["feature_names"])
    explanations["survSHAP"][i] = list(explanations["survSHAP"][i])[:10]
    explanations["survLIME"][i] = list(explanations["survLIME"][i]["hazard_ratios"].index)
print("hey")
os.getcwd()

    # Save it 
with open('/Users/abdallah/Desktop/Kings College Project/Code/Data prepation ELSA Dementia/DATA/explanations_fidelity.pkl', 'wb') as fp:
    pickle.dump(explanations, fp)
    print('explanations dictionary saved successfully to file')

    # Can start from here again
with open('/Users/abdallah/Desktop/Kings College Project/Code/Data prepation ELSA Dementia/DATA/explanations_fidelity.pkl', 'rb') as fp:
    explanations = pickle.load(fp)



# Calculate mean time in seconds it took for each explanation 
# (however, keep in mind: we did 16, not 10 features for survMLeX and had to weigh by sampling because there is no weights argument yet for the survival SVM)

np.mean(timer["survMLeX"]) #648.3481119704246
np.mean(timer["survChoquEx"]) #63.95492235660553
np.mean(timer["survSHAP"]) #240.07871958732605
np.mean(timer["survLIME"]) #1.0736926412582397


# Now fit a cox regression with the k=[3,5,10] most important features from each explanation and all their interactions for each explanation method and calculate the fidelity

fidelity = {}
fidelity["survMLeX"] = {}
fidelity["survChoquEx"] = {}
fidelity["survLIME"] = {}
fidelity["survSHAP"] = {}

    # TODO Skip another fidelity calculation I already have that. look at the explanations for the report


for tool in list(explanations.keys()):
    for k in [3,5,10]:
        fidelity[tool][k] = list()
        for counter, instance in enumerate(list(test.index)[:100]):
            instance_id = instance
            instance = np.array(test.drop(["time","dem_hse_w8"],axis=1).loc[instance_id,:]) 

                # generate a perturbed dataset around the instance
            scaled_data, inverse, weights = surv_utils.create_weighted_perturbed_data(explainer_fidelity.train_x, instance, explainer_fidelity.cat_indices, False, n=2000)

                # Get predictions for perturbed data
            surv_curves_pert_bb = explainer_fidelity.blackboxmodel.predict_survival_function(inverse, return_array=True)

                # Aggregate the predicted survival curves to achieve time-to-event estimates for perturbed data
            predictions_pert = surv_utils.aggregate_surv_function(surv_curves_pert_bb, "median", threshold = explainer_fidelity.threshold_blackbox_clf, timestamps = explainer_fidelity.time_stamps)
            x, y_lasso = surv_utils.convert_time_y_to_surv_y(df = predictions_pert, y = "time", event_indicator = "event", only_targets = False, round_y= False)

                # fit a Cox regression on the k most important predictors and all their interactions. 
            scaled_data = scaled_data[explanations[tool][counter][:k]]
            scaled_data = surv_utils.add_all_interactions_to_df(scaled_data) # Add all interactions

                # Use that Cox regression to give a prediction (survival function)
            if len(list(scaled_data.columns)) >20:
                k_lasso= 20
            else:
                k_lasso= len(list(scaled_data.columns)) 

            try:
                result = surv_utils.train_cox_and_explain( 
                            k_lasso, 
                            scaled_data, 
                            y_lasso, 
                            surv_curves_pert_bb, 
                            explainer_fidelity.time_stamps, 
                            False,
                            False,
                            alpha_min_ratio=0.01,
                            plot_curve=False)
            except: 
                result = {"hazard_ratios":np.nan, "survival_curve_bb": np.nan, "timestamps_bb":np.nan, 
                                            "survival_curve_cox":np.nan, "timestamps_cox":np.nan,"explanation_text":np.nan,
                                            "dementia_prob_10_years":np.nan, "fidelity":np.nan, "interpretable_model":np.nan }
                # Calculate the fidelity 
            fidelity[tool][k].append(result["fidelity"])
            print("Instance ", counter,": Fidelity for ",tool, " at k=",k, " is: ", result["fidelity"], "\n\n")

print("hey")

# Save the results up so far
results_fidelity = pd.DataFrame()




for tool in list(explanations.keys()):
    for k in [3,5,10]:
        results_fidelity["{}_{}".format(tool,k)] = fidelity[tool][k]
results_fidelity.to_csv("/Users/abdallah/Desktop/Kings College Project/Code/results/fidelity/results_fidelity.csv")

    # Can START FROM HERE AGAIN 
results_fidelity = pd.read_csv("/Users/abdallah/Desktop/Kings College Project/Code/results/fidelity/results_fidelity.csv",index_col=0)

    # Deal with NANs



# Then take mean fidelity for each k number of features and plot the CIs (take code from simulation)
for column in list(results_fidelity.columns):
    mean_value=results_fidelity[column].mean()
    results_fidelity[column].fillna(value=mean_value, inplace=True)

x = list(results_fidelity.columns)
y = list(results_fidelity.mean())
lower = list(results_fidelity.mean()) - 1.96*(list(results_fidelity.std())/np.sqrt(100))
upper = list(results_fidelity.mean()) + 1.96*(list(results_fidelity.std())/np.sqrt(100))

fidelity_confidence_intervals = {"x":x,
                            "y":y,
                            "lower":lower,
                            "upper":upper
                            }
fidelity_confidence_intervals = pd.DataFrame(fidelity_confidence_intervals)

fidelity_confidence_intervals.index = fidelity_confidence_intervals["x"]


fidelity_confidence_intervals
# Save the results for the confidence intervals 
fidelity_confidence_intervals.loc[["survMLeX_3", "survChoquEx_3", "survLIME_3", "survSHAP_3"],:].to_csv("/Users/abdallah/Desktop/Kings College Project/Code/results/fidelity/fidelity_confidence_intervals_k3.csv")
fidelity_confidence_intervals.loc[["survMLeX_5", "survChoquEx_5", "survLIME_5", "survSHAP_5"],:].to_csv("/Users/abdallah/Desktop/Kings College Project/Code/results/fidelity/fidelity_confidence_intervals_k5.csv")
fidelity_confidence_intervals.loc[["survMLeX_10", "survChoquEx_10", "survLIME_10", "survSHAP_10"],:].to_csv("/Users/abdallah/Desktop/Kings College Project/Code/results/fidelity/fidelity_confidence_intervals_k10.csv")

# Now calculate and plot the 95% confidence intervals for each using the R script, as well as the ANOVA and posthoc tests













# Case study
    # For SVM
orderingsSVM = pd.DataFrame(np.zeros((10,len(selected_features))))
orderingsSVM.columns = selected_features
for explanation in explanations["SVM"]: # Replace that with whatever tool I want and make a table
    for index, feature in enumerate(explanation[:10]):
        orderingsSVM.loc[index, feature] += 1

    # For ChoquEx
orderingsChoquEx = pd.DataFrame(np.zeros((10,len(selected_features))))
orderingsChoquEx.columns = selected_features
for explanation in explanations["survChoquEx"]: # Replace that with whatever tool I want and make a table
    for index, feature in enumerate(explanation[:10]):
        orderingsChoquEx.loc[index, feature] += 1



    # Get a global measure of feature importance
        #For SurvMLeX
global_mlex = nonadditive_explainer(explainer_fidelity.train_x.iloc[:1000,:], explainer_fidelity.train_y[:1000], method = "SurvMLeX", alpha=1.0, finetune=True, rank_ratio=1.0, fit_intercept=False, n_shuffle_splits=5, random_state=random_state, range_alpha= (2.0 ** np.arange(-8, 7, 2)))
global_mlex

        #For SurvChoquEx
global_choquex = nonadditive_explainer(explainer_fidelity.train_x.iloc[:1000,:], explainer_fidelity.train_y[:1000], method = "SurvChoquEx", alpha=1.0, finetune=True, rank_ratio=1.0, fit_intercept=False, n_shuffle_splits=5, random_state=random_state, range_alpha= (2.0 ** np.arange(-8, 7, 2)))
global_choquex

        #According to PFI
global_pfi = explainer_fidelity.global_feature_importance()
global_pfi

sum(data_w1_dummied["dem_hse_w8"])


    # SVM: Those are the top 5 features that are most important, 2nd most important, 3rd most importnat (make table)
for rank in range(6):
    orderingsSVM.sort_values(by=rank, axis=1).iloc[rank,-5:]


    # ChoquEx: Those are the top 5 features that are most important, 2nd most important, 3rd most importnat (make table)
for rank in range(5):
    orderingsChoquEx.sort_values(by=rank, axis=1).iloc[rank,-5:]


explanations.keys()


    # Put all those features in a Cox regression to see the nature of their relationship with dementia (look at the hazard ratios)

set_config(display="text")  # displays text representation of estimators
estimator = CoxPHSurvivalAnalysis()
estimator.fit(explainer_fidelity.train_x, explainer_fidelity.train_y)
pd.Series(estimator.coef_, index=explainer_fidelity.train_x.columns) # Negative sign means PROTECTIVE effect. So being white, male etc is bad and ....

    # Add all interactions and try again with penalised Cox regression


from sksurv.linear_model import CoxPHSurvivalAnalysis, CoxnetSurvivalAnalysis
from sksurv.preprocessing import OneHotEncoder

from sklearn import set_config
from sklearn.model_selection import GridSearchCV, KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


explainer_fidelity.train_x

Xt = surv_utils.add_all_interactions_to_df(explainer_fidelity.train_x, order=2).copy()
y = explainer_fidelity.train_y.copy()




alphas = 10.0 ** np.linspace(-4, 4, 50)
coefficients = {}

cph = CoxPHSurvivalAnalysis()
for alpha in alphas:
    cph.set_params(alpha=alpha)
    cph.fit(Xt, y)
    key = round(alpha, 5)
    coefficients[key] = cph.coef_

coefficients = pd.DataFrame.from_dict(coefficients).rename_axis(index="feature", columns="alpha").set_index(Xt.columns)


def plot_coefficients(coefs, n_highlight):
    _, ax = plt.subplots(figsize=(9, 6))
    n_features = coefs.shape[0]
    alphas = coefs.columns
    for row in coefs.itertuples():
        ax.semilogx(alphas, row[1:], ".-", label=row.Index)

    alpha_min = alphas.min()
    top_coefs = coefs.loc[:, alpha_min].map(abs).sort_values().tail(n_highlight)
    for name in top_coefs.index:
        coef = coefs.loc[name, alpha_min]
        plt.text(alpha_min, coef, name + "   ", horizontalalignment="right", verticalalignment="center")

    ax.yaxis.set_label_position("right")
    ax.yaxis.tick_right()
    ax.grid(True)
    ax.set_xlabel("alpha")
    ax.set_ylabel("coefficient")


plot_coefficients(coefficients, n_highlight=5)
plt.show()



    # See which 40 features remain with Lasso
k_features=40
scaled_data = Xt.copy()
y_lasso = y.copy()
alpha_min_ratio=0.01
k_features_found = False
counter = 0
explanation = dict()
while k_features_found==False:
    cox_lasso = CoxnetSurvivalAnalysis(l1_ratio=1.0, alpha_min_ratio=alpha_min_ratio, fit_baseline_model = True)
    cox_lasso.fit(scaled_data, y_lasso)  
        # Investigate how many features remain for each alpha
    coefficients_lasso = pd.DataFrame(
        cox_lasso.coef_,
        index=scaled_data.columns,
        columns=np.round(cox_lasso.alphas_, 5)
    )
    
    if any(np.array(np.sum(np.absolute(coefficients_lasso)> 0))==k_features): 
        k_features_found = True
        alpha = coefficients_lasso.columns[np.array(np.sum(np.absolute(coefficients_lasso)> 0))==k_features][0]
        column_index = list(np.array(np.sum(np.absolute(coefficients_lasso)> 0))==k_features).index(True)
        print("{} features found for alpha_min_ratio {} at alpha {} in column_index {}.".format(k_features, alpha_min_ratio, alpha, column_index))
        explanation["coefficients_alpha_matrix"] = coefficients_lasso
        explanation["alpha"] = alpha
    else:
        alpha_min_ratio = alpha_min_ratio/2
        counter += 1
        if counter > 100:
            print("No suitable alpha found even after 100 iterations: consider quitting running time.")
        if counter >1000:
            print("No alpha found for {}. Trying to select {} most important features".format(k_features, k_features+1))
            k_features= k_features+1
        if counter >2000:
            print("No alpha found for {}. Trying to select {} most important features".format(k_features, k_features-2))
            k_features= k_features-2
        if counter >3000:
            assert("No suited alpha for specified number of features found.")

    # Here the 40 most important features/interactions
coefficients_lasso.loc[coefficients_lasso.loc[:,alpha] != 0.0,alpha].sort_values(key=abs)

    # For the partial dependence plots I can use R. Will save the df for that purpose
explainer_fidelity.train.to_csv("/Users/abdallah/Desktop/Kings College Project/Code/results/case_study/selected_elsa_df.csv")



    # Plot some interactions
    # Most important ones: ethnicity and processing speed (-0.29), age and processing speed (0.17), age and absence of an educational qualification (-0.15), as well as social participation and religiosity (0.07). 
import seaborn 
import matplotlib.pyplot as plt

#     #
# explainer_fidelity.train_x["ethnicity_White"].value_counts()
# explainer_fidelity.train_x["procspeed1"]

    #

data_w1_dummied_unstandardised["age_over_70"] = [1. if x >69 else 0. for x in data_w1_dummied_unstandardised["age"]]
ax = seaborn.lmplot(x="procspeed1",markers='*', scatter_kws={'alpha':0.3}, hue="age_over_70", y="time", y_jitter=0.3, x_jitter=0.3,data=data_w1_dummied_unstandardised)
ax.set(xlabel='Processing Speed', ylabel='Time to Dementia')
ax._legend.set_title("Age")
new_labels = ['< 70', '> 70']
for t, l in zip(ax._legend.texts, new_labels):
    t.set_text(l)

# Access the legend object and set frameon to True
ax._legend.set_frame_on(True)
ax._legend.set_bbox_to_anchor((1, 0.3))

plt.show()


#     #
# explainer_fidelity.train_x["age"]
# explainer_fidelity.train_x["edqual_No qualification"].value_counts()
# seaborn.lmplot(x="age", 
#                hue="edqual_No qualification", 
#                y="time", 
#                markers='*', 
#                data=training) 
# plt.show()

    #
explainer_fidelity.train_x["scorg3"].value_counts()
explainer_fidelity.train_x["social"].value_counts()




data_w1_dummied_unstandardised["social"] = data_w1_dummied["social"]
ax = seaborn.lmplot(x="social",markers='*', scatter_kws={'alpha':0.3},  hue="scorg3", y="time", y_jitter=0.3, x_jitter=0.3, data=data_w1_dummied_unstandardised)

ax.set(xlabel='Social Participation', ylabel='Time to Dementia')
ax._legend.set_title("Part of Religious Group")
new_labels = ['No', 'Yes']
for t, l in zip(ax._legend.texts, new_labels):
    t.set_text(l)

# Access the legend object and set frameon to True
ax._legend.set_frame_on(True)
ax._legend.set_bbox_to_anchor((1.2, 0.3))

plt.show()
np.mean(data_w1_dummied_unstandardised.loc[data_w1_dummied_unstandardised["scorg3"]==0,"time"])



