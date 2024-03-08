import os 
os.chdir('/Users/abdallah/Desktop/Kings College Project/Code/GIT_Repo')
from explainer import ExplainSurvival
from sksurv.datasets import load_veterans_lung_cancer
from sksurv.preprocessing import OneHotEncoder
from sksurv.ensemble import RandomSurvivalForest

    # Import survival data
data_x, data_y = load_veterans_lung_cancer()
    # Onehot encode the dataset in order to train the survival model 
data_x = OneHotEncoder().fit_transform(data_x)
    # Save names of categorical features (needed as an argument for the explainer) AFTER one-hot-encoding 
cat_features = ['Prior_therapy=yes','Treatment=test', 'Celltype=large', 'Celltype=smallcell',
       'Celltype=squamous']
    # Train (for instance) a random survival forest
rsf = RandomSurvivalForest(
    n_estimators=1000, min_samples_split=10, min_samples_leaf=15, n_jobs=-1, random_state=1
)
rsf.fit(data_x, data_y)
    # Select an instance to explain
i = data_x.iloc[0,:]

    # Create an explainer object
explainer = ExplainSurvival(
                 model = rsf, # the model whose output we want to explain 
                 x = data_x, # DUMMIED data that was used to train the blackbox model
                 y = data_y, # the outcome data in a format suitable for sklearn survival models  
                 categorical_features = cat_features, # List of strings of the feature labels corresponding to categorical features
                 random_state = None, # random state for intilisation of random functions
                 )

    # Explain an instance using any of the four methods "SurvMLeX", "SurvChoquEx", "SurvLIME" or "SurvSHAP"
explanation = explainer.explain_instance( 
                        instance = i , # Pass instance as a np.array or pd.series                         
                        method = "SurvLIME", # Explanation method: either "SurvMLeX", "SurvChoquEx", "SurvLIME" or "SurvSHAP"
                        binary=False, # Using a binary representation for the perturbed samples. Default is False
                        aggregation_method = "percentile", # How to aggregate survival function predictions to a time-to-event estimate: "trapezoid", "median" or "percentile"
                        threshold_aggregation = 0.5, # Which threshold to use when aggregating survival curves to a time-to-event estimate using the percentile method (if it is not finetuned)
                        find_best_cutoff = True, # Finds optimal value for threshold_blackbox_clf argument
                        n_perturbed=1000, # Size of the perturbed dataset
                        weighing_multiplier = 2.0, # How much larger the perturbed dataset will be after weighing through sampling with replacement  
                        finetune_explainer=True, # Whether to finetune expainer (only for SurvMLeX, SurvChoquEx and SurvSHAP)
                        only_shapley_values=False, # Not relevant if method="SurvLIME". For other methods it wont use identified features to fit a Cox regression model but give the shapley values right away
                        k_features=3, # The number of features to retain if a penalised Cox regression is fit (only if only_shapley_values=False)
                        plot_curve=True, # Whether explainer should also plot survival curve (only if only_shapley_values=False)
                        alpha_min_ratio=0.01, # alpha_min_ratio argument for the penalised Cox regression (only if only_shapley_values=False)
                        alpha=1.0, # Alpha parameter of SurvMLeX or SurvChoquEx
                        survshap_calculation_method="sampling" # for survshap method: can be either "kernel", "sampling", "treeshap" or "shap_kernel"
                        )

    # retrieve the shapley values and other useful data from the explanation object
explanation["shapley_values"] 
explanation["explanation_text"]

    # You can also get a global measure of feature importance using SurvMLeX or SurvChoquEx
    # Simply apply the methods on the entire dataset
from nonadditive_explainers import nonadditive_explainer
import numpy as np
global_importance = nonadditive_explainer(data_x, data_y, method = "SurvMLeX", alpha=0.1, finetune=True, rank_ratio=1.0, fit_intercept=False, n_shuffle_splits=5, random_state=1, range_alpha= (2.0 ** np.arange(-8, 7, 2)))


    # TODO maybe also show how to apply it to different packages besides sklearn


