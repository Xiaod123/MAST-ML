import os
import matplotlib
import numpy as np
import data_parser
import matplotlib.pyplot as plt
from mean_error import mean_error
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error
import data_analysis.printout_tools as ptools
import plot_data.plot_predicted_vs_measured as plotpm
import plot_data.plot_xy as plotxy
from SingleFit import SingleFit
from LeaveOutPercentCV import LeaveOutPercentCV
from SingleFit import timeit
from sklearn.metrics import r2_score

class KFoldCV(LeaveOutPercentCV):
    """KFold cross validation
   
    Args:
        training_dataset, (Should be the same as testing_dataset)
        testing_dataset, (Should be the same as training_dataset)
        model,
        save_path,
        input_features,
        target_feature,
        target_error_feature,
        labeling_features, 
        xlabel, 
        ylabel,
        stepsize,
        mark_outlying_points,
        num_cvtests,
        fix_random_for_testing, see parent class.
        num_folds <int>: Number of folds for KFold CV
 
    Returns:
        Analysis in the save_path folder
        Plots results in a predicted vs. measured square plot.
    Raises:
        ValueError if testing target data is None; CV must have
                testing target data
    """
    def __init__(self, 
        training_dataset=None,
        testing_dataset=None,
        model=None,
        save_path=None,
        input_features=None,
        target_feature=None,
        target_error_feature=None,
        labeling_features=None,
        xlabel="Measured",
        ylabel="Predicted",
        stepsize=1,
        mark_outlying_points=None,
        num_cvtests=10,
        fix_random_for_testing=0,
        num_folds=2,
        *args, **kwargs):
        """
        Additional class attributes to parent class:
            Set by keyword:
            self.num_folds <int>: Number of folds for KFold test
            Set in code:
        """
        if not(training_dataset == testing_dataset):
            raise ValueError("Only testing_dataset will be used. Use the same values for training_dataset and testing_dataset")
        LeaveOutPercentCV.__init__(self, 
            training_dataset=training_dataset, #only testing_dataset is used
            testing_dataset=testing_dataset,
            model=model, 
            save_path = save_path,
            input_features = input_features, 
            target_feature = target_feature,
            target_error_feature = target_error_feature,
            labeling_features = labeling_features,
            xlabel=xlabel,
            ylabel=ylabel,
            stepsize=stepsize,
            mark_outlying_points = mark_outlying_points,
            percent_leave_out = -1, #not using this field
            num_cvtests = num_cvtests,
            fix_random_for_testing = fix_random_for_testing)
        self.num_folds = int(num_folds)
        return 

    @timeit
    def plot(self):
        self.readme_list.append("----- Plotting -----\n")
        notelist=list()
        notelist.append("Mean over %i tests of:" % self.num_cvtests)
        notelist.append("  {:d}-fold-average RMSE:".format(self.num_folds))
        notelist.append("    {:.2f} $\pm$ {:.2f}".format(self.statistics['avg_fold_avg_rmses'], self.statistics['std_fold_avg_rmses']))
        notelist.append("  {:d}-fold-average mean error:".format(self.num_folds))
        notelist.append("    {:.2f} $\pm$ {:.2f}".format(self.statistics['avg_fold_avg_mean_errors'], self.statistics['std_fold_avg_mean_errors']))
        self.plot_best_worst_overlay(notelist=list(notelist))
        return

    def set_up_cv(self):
        if self.testing_target_data is None:
            raise ValueError("Testing target data cannot be none for cross validation.")
        indices = np.arange(0, len(self.testing_target_data))
        self.readme_list.append("----- CV setup -----\n")
        self.readme_list.append("%i CV tests,\n" % self.num_cvtests)
        self.readme_list.append("each with %i folds\n" % self.num_folds)
        self.cvmodel = KFold(n_splits = self.num_folds, shuffle=True, 
                                random_state = None)
        for cvtest in range(0, self.num_cvtests):
            self.cvtest_dict[cvtest] = dict()
            foldidx=0
            fold_rmses = np.zeros(self.num_folds)
            for train, test in self.cvmodel.split(indices):
                fdict=dict()
                fdict['train_index'] = train
                fdict['test_index'] = test
                self.cvtest_dict[cvtest][foldidx] = dict(fdict)
                foldidx = foldidx + 1
        return
    
    def cv_fit_and_predict(self):
        for cvtest in self.cvtest_dict.keys():
            fold_rmses = np.zeros(self.num_folds)
            fold_mean_errors = np.zeros(self.num_folds)
            fold_array = np.zeros(len(self.testing_target_data))
            prediction_array = np.zeros(len(self.testing_target_data))
            for fold in self.cvtest_dict[cvtest].keys():
                fdict = self.cvtest_dict[cvtest][fold]
                input_train = self.testing_input_data[fdict['train_index']]
                target_train = self.testing_target_data[fdict['train_index']]
                input_test = self.testing_input_data[fdict['test_index']]
                target_test = self.testing_target_data[fdict['test_index']]
                fit = self.model.fit(input_train, target_train)
                predict_test = self.model.predict(input_test)
                rmse = np.sqrt(mean_squared_error(predict_test, target_test))
                merr = mean_error(predict_test, target_test)
                fold_rmses[fold] = rmse
                fold_mean_errors[fold] = merr
                fold_array[fdict['test_index']] = fold
                prediction_array[fdict['test_index']] = predict_test
            self.cvtest_dict[cvtest]["avg_rmse"] = np.mean(fold_rmses)
            self.cvtest_dict[cvtest]["std_rmse"] = np.std(fold_rmses)
            self.cvtest_dict[cvtest]["avg_mean_error"] = np.mean(fold_mean_errors)
            self.cvtest_dict[cvtest]["std_mean_error"] = np.std(fold_mean_errors)
            self.cvtest_dict[cvtest]["fold_array"] = fold_array
            self.cvtest_dict[cvtest]["prediction_array"] = prediction_array
        return

    def get_statistics(self):
        cvtest_avg_rmses = list()
        cvtest_avg_mean_errors = list()
        for cvtest in range(0, self.num_cvtests):
            cvtest_avg_rmses.append(self.cvtest_dict[cvtest]["avg_rmse"])
            cvtest_avg_mean_errors.append(self.cvtest_dict[cvtest]["avg_mean_error"])
        highest_rmse = max(cvtest_avg_rmses)
        self.worst_test_index = cvtest_avg_rmses.index(highest_rmse)
        lowest_rmse = min(cvtest_avg_rmses)
        self.best_test_index = cvtest_avg_rmses.index(lowest_rmse)
        self.statistics['avg_fold_avg_rmses'] = np.mean(cvtest_avg_rmses)
        self.statistics['std_fold_avg_rmses'] = np.std(cvtest_avg_rmses)
        self.statistics['avg_fold_avg_mean_errors'] = np.mean(cvtest_avg_mean_errors)
        self.statistics['std_fold_avg_mean_errors'] = np.std(cvtest_avg_mean_errors)
        self.statistics['fold_avg_rmse_best'] = lowest_rmse
        self.statistics['fold_avg_rmse_worst'] = highest_rmse
        return

    def print_output_csv(self, label="", cvtest_entry=None):
        """
            Modify once dataframe is in place
        """
        olabel = "%s_test_data.csv" % label
        ocsvname = os.path.join(self.save_path, olabel)
        self.readme_list.append("%s file created with columns:\n" % olabel)
        headerline = ""
        printarray = None
        if len(self.labeling_features) > 0:
            self.readme_list.append("   labeling features: %s\n" % self.labeling_features)
            print_features = list(self.labeling_features)
        else:
            print_features = list()
        print_features.extend(self.input_features)
        self.readme_list.append("   input features: %s\n" % self.input_features)
        if not (self.testing_target_data is None):
            print_features.append(self.target_feature)
            self.readme_list.append("   target feature: %s\n" % self.target_feature)
            if not (self.target_error_feature is None):
                print_features.append(self.target_error_feature)
                self.readme_list.append("   target error feature: %s\n" % self.target_error_feature)
        for feature_name in print_features:
            headerline = headerline + feature_name + ","
            feature_vector = np.asarray(self.testing_dataset.get_data(feature_name)).ravel()
            if printarray is None:
                printarray = feature_vector
            else:
                printarray = np.vstack((printarray, feature_vector))
        headerline = headerline + "Prediction,"
        self.readme_list.append("   prediction: Prediction\n")
        printarray = np.vstack((printarray, cvtest_entry['prediction_array']))
        headerline = headerline + "Fold"
        self.readme_list.append("   fold number: Fold\n")
        printarray = np.vstack((printarray, cvtest_entry['fold_array']))
        printarray=printarray.transpose()
        ptools.mixed_array_to_csv(ocsvname, headerline, printarray)
        return
