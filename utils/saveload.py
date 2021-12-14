# -*- coding: utf-8 -*-
"""Various functions related to saving and loading of weights and optimizer
states."""
from __future__ import print_function, absolute_import
import os
import os.path
import re
from utils.History import History

def load_previous_model(identifier, model, la_plotter,
                        weights_dir, csv_filepath):
    """Loads the data (weights, history, plot) of a previous experiment
    that had the provided identifier.

    Args:
        identifier: Identifier of the previous experiment.
        model: The current model. That model's weights will be changed to the
            loaded ones. Architecture (layers) must be identical.
        la_plotter: The current plotter for loss and accuracy. Will be updated
            with the loaded history data.
        weights_dir: Directory where model weights are saved.
        csv_filepath: Filepath to the csv file containing the history data
            of that experiment.

    Returns:
        Will return a tupel (last epoch, history), where "last epoch" is the
        last epoch that was finished in the old experiment and "history"
        is the old experiment's history object (i.e. epochs, loss, acc).
    """
    # load weights
    # we overwrite the results of the optimizer loading here, because errors
    # there are not very important, we can still go on training.
    (success, last_epoch) = load_weights(model, weights_dir, identifier)

    if not success:
        raise Exception("Cannot continue previous experiment, because no " \
                        "weights were saved (yet?).")

    # load history from csv file
    history = History()
    history.load_from_file(csv_filepath.format(identifier=identifier),
                           last_epoch=last_epoch)

    # update loss acc plotter
    for i, epoch in enumerate(history.epochs):
        la_plotter.add_values(epoch,
                              loss_train=history.loss_train[i],
                              loss_val=history.loss_val[i],
                              acc_train=history.acc_train[i],
                              acc_val=history.acc_val[i],
                              redraw=False)

    return history.epochs[-1], history

def load_weights(model, save_weights_dir, previous_identifier):
    """Load the weights of an older experiment into a model.

    This function searches for files called
    "<previous_identifier>.at1234.weights"
    or "<previous_identifier>.last.weights" (wehre at1234 represents epoch
    1234). If a *.last file was found, that one will be used. Otherwise the
    weights file with the highest epoch number will be used.

    The new and the old model must have identical architecture/layers.

    Args:
        model: The model for which to load the weights. The current weights
            will be overwritten.
        save_weights_dir: The directory in which weights are saved.
        previous_identifier: Identifier of the old experiment.
    Returns:
        Either tuple (bool success, int epoch)
            or tuple (bool success, string "last"),
        where "success" indicates whether a weights file was found
        and "epoch" represents the epoch of that weights file (e.g. 1234 in
        *.at1234) and "last" represents a *.last file.
    """
    filenames = [f for f in os.listdir(save_weights_dir) \
                         if os.path.isfile(os.path.join(save_weights_dir, f))]
    filenames = [f for f in filenames \
                         if f.startswith(previous_identifier + ".") and \
                            f.endswith(".weights")]
    if len(filenames) == 0:
        return (False, -1)
    else:
        filenames_last = [f for f in filenames if f.endswith(".last.weights")]
        if len(filenames_last) >= 2:
            raise Exception("Ambiguous weight files for model, multiple " \
                            "files match description.")
        if len(filenames_last) == 1:
            weights_filepath = os.path.join(save_weights_dir, filenames_last[0])
            #load_weights_seq(model, weights_filepath)
            model.load_weights(weights_filepath)
            return (True, "last")
        else:
            # If we have a filename, e.g. "model1.at500.weights", we split it
            # at every "." so that we get ["model1", "at500", "weights"], we
            # then pick the 2nd entry ("at500") and convert the digits to an
            # integer (500). We sort the list of ints in reverse to have the
            # highest value at the first position (e.g. [500, 400, 300, ...]).
            epochs = [int(re.sub("[^0-9]", "", f.split(".")[1])) for f in \
                      filenames]
            epochs = sorted(epochs, reverse=True)
            fname = "{}.at{}.weights".format(previous_identifier, epochs[0])
            weights_filepath = os.path.join(save_weights_dir, fname)
            model.load_weights(weights_filepath)
            return (True, epochs[0])
