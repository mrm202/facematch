# -*- coding: utf-8 -*-
"""File with helper functions to load test/validation/training sets from
the root dataset of Labeled Faces in the Wild, grayscaled and cropped (which
must already be on the hard drive).

The main function to use is get_image_pairs().
"""
from __future__ import absolute_import, division, print_function
import random
import re
import os
from collections import defaultdict
from scipy import misc
import numpy as np
import cv2
import matplotlib.pyplot as plt

Y_SAME = 1
Y_DIFFERENT = 0
IMAGE_CHANNELS = 1

class ImageFile(object):
    """Object to model one image file of the dataset.
    Example:
      image_file = ImageFile("~/lfw-gc/faces/", "Arnold_Schwarzenegger_001.pgm")
    """
    def __init__(self, directory, name):
        """Initialize the ImageFile object.
        Args:
            directory: Directory of the file.
            name: Full filename, e.g. 'foo.txt'."""
        self.filepath = os.path.join(directory, name)
        self.filename = name
        self.person = filepath_to_person_name(self.filepath)
        self.number = filepath_to_number(self.filepath)

    def get_content(self):
        """Returns the content of the image (pixel values) as a numpy array.

        Returns:
            Content of image as numpy array (dtype: uint8).
            Should have shape (height, width) as the images are grayscaled."""
        if IMAGE_CHANNELS == 3:
            img = cv2.imread(self.filepath)
        else:
            img = cv2.imread(self.filepath, 0)
            assert len(img.shape) == 2
            img = img[:, :, np.newaxis]
        return img

class ImagePair(object):
    """Object that models a pair of images, used during training of the neural
    net.
    Use the instance variables
        - 'same_person' to determine whether both images of the pair
           show the same person and
        - 'same_image' whether both images of the pair are identical.
    """
    def __init__(self, image1, image2):
        """Create a new ImagePair object.
        Args:
            image1: ImageFile object of the first image in the pair.
            image2: ImageFile object of the second image in the pair.
        """
        self.image1 = image1
        self.image2 = image2
        self.same_person = (image1.person == image2.person)
        self.same_image = (image1.filepath == image2.filepath)

    def get_key(self, ignore_order):
        """Return a key to represent this pair, e.g. in sets.

        Returns:
            A (string-)key representing this pair.
        """
        # if ignore_order then (image1,image2) == (image2,image1)
        # therefore, the key used to check if a pair already exists must then
        # catch both cases (A,B) and (B,A), i.e. it must be sorted to always
        # be (A,B)
        # Could probably use tuples here as keys too.
        fps = [self.image1.filepath, self.image2.filepath]
        if ignore_order:
            key = "$$$".join(sorted(fps))
        else:
            key = "$$$".join(fps)
        return key

    def get_contents(self, height, width):
        """Returns the contents (pixel values) of both images of the pair as
        one numpy array.
        Args:
            height: Output height of each image.
            width: Output width of each image.
        Returns:
            Numpy array of shape (2, height, width) with dtype uint8.
        """
        img1 = self.image1.get_content()
        img2 = self.image2.get_content()
        if img1.shape[0] != height or img1.shape[1] != width:
            # imresize can only handle (height, width) or (height, width, 3),
            # not (height, width, 1), so squeeze away the last channel
            if IMAGE_CHANNELS == 1:
              img1 = cv2.resize(img1, (height,width))
              img1 = np.squeeze(img1)
              #img1 = misc.imresize(np.squeeze(img1), (height, width))
              img1 = img1[:, :, np.newaxis]
            else:
                img1 = cv2.resize(img1, (height,width))
        if img2.shape[0] != height or img2.shape[1] != width:
            if IMAGE_CHANNELS == 1:
                img2 = cv2.resize(img2, (height,width))
                img2 = np.squeeze(img2)
                #img2 = misc.imresize(np.squeeze(img2), (height, width))
                img2 = img2[:, :, np.newaxis]
            else:
                img2 = cv2.resize(img2, (height,width))
                img2 = np.squeeze(img2)
                #img2 = misc.imresize(img2, (height, width))
                img2 = img2[:, :, np.newaxis]
        return np.array([img1, img2], dtype=np.uint8)
        '''if IMAGE_CHANNELS == 1:
                img1 = misc.imresize(np.squeeze(img1), (height, width))
                img1 = img1[:, :, np.newaxis]
            else:
                img1 = misc.imresize(img1, (height, width))
        if img2.shape[0] != height or img2.shape[1] != width:
            if IMAGE_CHANNELS == 1:
                img2 = misc.imresize(np.squeeze(img2), (height, width))
                img2 = img2[:, :, np.newaxis]
            else:
                img2 = misc.imresize(img2, (height, width))
        return np.array([img1, img2], dtype=np.uint8)'''

def filepath_to_person_name(filepath):
    """Extracts the name of a person from a filepath.
    Obviously only works with the file naming used in the LFW-GC dataset.

    Args:
        fp: The full filepath of the file.
    Returns:
        Name of the person.
    """
    last_slash = filepath.rfind("/")
    if last_slash is None:
        return filepath[0:filepath.rfind("_")]
    else:
        return filepath[last_slash+1:filepath.rfind("_")]

def filepath_to_number(filepath):
    """Extracts the number of the image from a filepath.

    Each person in the dataset may have 1...N images associated with him/her,
    which are then numbered from 1 to N in the filepath. This function returns
    that number.

    Args:
        filepath: The full filepath of the file.
    Returns:
        Number of that image (among all images of that person).
    """
    fname = os.path.basename(filepath)
    return int(re.sub(r"[^0-9]", "", fname))

def get_image_files(dataset_filepath, exclude_images=None):
    """Loads all images sorted by filenames and returns them as ImageFile
    Objects.

    Args:
        dataset_filepath: Path to the 'faces/' subdirectory of the dataset
            (Labeled Faces in the Wild, grayscaled and cropped).
        exclude_images: List of ImageFile objects to exclude from the list to
            return, e.g. because they are already used for another set of
            images (training, validation, test).
    Returns:
        List of ImageFile objects containing all images in the dataset filepath,
        except for the ones in exclude_images.
    """
    if not os.path.isdir(dataset_filepath):
        raise Exception("Images filepath '%s' of the dataset seems to not " \
                        "exist or is not a directory." % (dataset_filepath,))

    images = []
    exclude_images = exclude_images if exclude_images is not None else set()
    exclude_filenames = set()
    for image_file in exclude_images:
        exclude_filenames.add(image_file.filename)

    for directory, subdirs, files in os.walk(dataset_filepath):
        for name in files:
            if re.match(r"^.*_[0-9]+\.(pgm|ppm|jpg|jpeg|png|bmp|tiff)$", name):
                if name not in exclude_filenames:
                    images.append(ImageFile(directory, name))
    images = sorted(images, key=lambda image: image.filename)
    return images

def get_image_pairs(dataset_filepath, nb_max, pairs_of_same_imgs=False,
                    ignore_order=True, exclude_images=None, seed=None,
                    verbose=False):
    """Creates a list of ImagePair objects from images in the dataset directory.

    This is the main method intended to load training/validation/test datasets.

    The images are all expected to come from the
        Labeled Faces in the Wild, grayscaled and cropped (sic!)
    dataset.
    Their names must be similar to:
        Adam_Scott_0002.pgm
        Kalpana_Chawla_0002.pgm

    Note: This function may currently run endlessly if nb_max is set too
    higher (above maximum number of possible pairs of same or different
    persons, whichever is lower - that number however is pretty large).

    Args:
        images_filepath: Path to the 'faces/' subdirectory of the dataset
            (Labeled Faces in the Wild, grayscaled and cropped).
        nb_max: Maximum number of image pairs to return. If there arent enough
            possible pairs, less pairs will be returned.
        pairs_of_same_imgs: Whether pairs of images may be returned, where
            filepath1 == filepath2. Notice that this may return many
            pairs of same images as many people only have low amounts of
            images. (Default is False.)
        ignore_order: Defines whether (image1, image2) shall be
            considered identical to (image2, image1). So if one
            of them is already added, the other pair wont be added any more.
            Setting this to True will result in less possible but more
            diverse pairs of images. (Default is True.)
        exclude_images: List of ImagePair objects with images that will be
            excluded from the result, i.e. no image that is contained in any
            pair in that list will be contained in any pair of the result of
            this function. Useful to fully separate validation and training
            sets.
        seed: A seed to use at the start of the function.
        verbose: Whether to print messages with statistics about the dataset
            and the collected images.
    Returns:
        List of ImagePair objects.
    """
    if seed is not None:
        state = random.getstate() # used right before the return
        random.seed(seed)

    # validate dataset directory
    if not os.path.isdir(dataset_filepath):
        raise Exception("Images filepath '%s' of the dataset seems to not " \
                        "exist or is not a directory." % (dataset_filepath,))

    # Build set of images to not use in image pairs (because they have
    # been used previously)
    exclude_images = exclude_images if exclude_images is not None else []
    exclude_images = set([img_pair.image1 for img_pair in exclude_images]
                         + [img_pair.image2 for img_pair in exclude_images])

    # load metadata of all images as ImageFile objects (except for the
    # excluded ones)
    images = get_image_files(dataset_filepath, exclude_images=exclude_images)

    # build a mapping person=>images[]
    # this will make it easier to do stratified sampling of images
    images_by_person = defaultdict(list)
    for image in images:
        images_by_person[image.person].append(image)

    nb_img = len(images)
    nb_people = len(images_by_person)

    # ----
    # Show some statistics about the dataset
    if verbose:
        def count_persons(start, end):
            """Counts how many people have an amount of images in a given
            range.
            Args:
                start: Start of the range (including).
                end: End of the range (excluding).
            Returns:
                Count of people with x images where start<=x<end."""
            names = [name for name, images in images_by_person.items() \
                          if len(images) >= start and len(images) < end]
            return len(names)

        print("Found %d images in filepath, resulting in theoretically max " \
              "k*(k-1)=%d ordered or (k over 2)=k(k-1)/2=%d unordered " \
              "pairs." % (nb_img, nb_img*(nb_img-1), nb_img*(nb_img-1)/2))
        print("Found %d different persons" % (nb_people,))
        print("In total...")
        print(" {:>7} persons have 1 image.".format(count_persons(1, 2)))
        print(" {:>7} persons have 2 images.".format(count_persons(2, 3)))
        print(" {:>7} persons have 3-5 images.".format(count_persons(3, 6)))
        print(" {:>7} persons have 6-10 images.".format(count_persons(6, 11)))
        print(" {:>7} persons have 11-25 images.".format(count_persons(11, 26)))
        print(" {:>7} persons have 26-75 images.".format(count_persons(26, 76)))
        print(" {:>7} persons have 76-200 images.".format(
            count_persons(76, 201))
        )
        print(" {:>7} persons have >=201 images.".format(
            count_persons(201, 9999999))
        )
    # ----

    # Create lists
    #  a) of all names of people appearing in the dataset
    #  b) of all names of people appearing in the dataset
    #     with at least 2 images
    names = []
    names_gte2 = []
    for person_name, images in images_by_person.items():
        names.append(person_name)
        if len(images) >= 2:
            names_gte2.append(person_name)

    # Calculate maximum amount of possible pairs of images showing the
    # same person (not identical with "good" pairs, e.g. may be 10,000
    # times Arnold Schwarzenegger)
    if verbose:
        sum_avail_ordered = 0
        sum_avail_unordered = 0
        for name in names_gte2:
            k = len(images_by_person[name])
            sum_avail_ordered += k*(k-1)
            sum_avail_unordered += k*(k-1)/2
        print("Can collect max %d ordered and %d unordered pairs of images " \
              "that show the _same_ person." \
              % (sum_avail_ordered, sum_avail_unordered))

    # ---
    # Build pairs of images
    #
    # We use stratified sampling over the person to sample images.
    # So we pick first a name among all available person names and then
    # randomly select an image of that person. (In contrast to picking a random
    # image among all images of all persons.) This makes the distribution of
    # the images more uniform over the persons. (In contrast to having a very
    # skewed distribution favoring much more people with many images.)
    # ---

    # result
    pairs = []

    # counters
    # only nb_added is really needed, we other ones are for print-output
    # in verbose mode
    nb_added = 0
    nb_same_p_same_img = 0 # pairs of images of same person, same image
    nb_same_p_diff_img = 0 # pairs of images of same person, different images
    nb_diff = 0

    # set that saves identifiers for pairs of images that have
    # already been added to the result.
    added = set()

    # -------------------------
    # y = 1 (pairs with images of the same person)
    # -------------------------
    while nb_added < nb_max // 2:
        # pick randomly two images and make an ImagePair out of them
        person = random.choice(names_gte2)
        image1 = random.choice(images_by_person[person])
        if pairs_of_same_imgs:
            image2 = random.choice(images_by_person[person])
        else:
            image2 = random.choice([image for image in \
                                    images_by_person[person] \
                                    if image != image1])

        pair = ImagePair(image1, image2)
        key = pair.get_key(ignore_order)

        # add the ImagePair to the output, if the same pair hasn't been already
        # picked
        if key not in added:
            pairs.append(pair)
            nb_added += 1
            nb_same_p_same_img += 1 if pair.same_image else 0
            nb_same_p_diff_img += 1 if not pair.same_image else 0
            # log this pair as already added (dont add it a second time)
            added.add(key)

    # -------------------------
    # y = 0 (pairs with images of different persons)
    # -------------------------
    while nb_added < nb_max:
        # pick randomly two different persons names to sample each one image
        # from
        person1 = random.choice(names)
        person2 = random.choice([person for person in names \
                                 if person != person1])

        # we dont have to check here whether the images are the same,
        # because they come from different persons
        image1 = random.choice(images_by_person[person1])
        image2 = random.choice(images_by_person[person2])
        pair = ImagePair(image1, image2)
        key = pair.get_key(ignore_order)

        # add the ImagePair to the output, if the same pair hasn't been already
        # picked
        if key not in added:
            pairs.append(pair)
            nb_added += 1
            nb_diff += 1
            # log this pair as already added (dont add it a second time)
            added.add(key)

    # Shuffle the created list
    random.shuffle(pairs)

    # Print some statistics
    if verbose:
        print("Collected %d pairs of images total." % (nb_added,))
        print("Collected %d pairs of images showing the same person (%d are " \
              "pairs of identical images)." % \
                (nb_same_p_same_img + nb_same_p_diff_img, nb_same_p_same_img))
        print("Collected %d pairs of images showing different persons." \
                % (nb_diff,))

    # reset the RNG to the state that it had before calling the method
    if seed is not None:
        random.setstate(state) # state was set at the start of this function

    return pairs

def image_pairs_to_xy(image_pairs, height, width):
    """Converts a list of ImagePair objects to X (array of pixel values) and
    Y (labels) to use during training/testing.

    Args:
        image_pairs: List of ImagePair objects.
    Returns:
        Tuple of X and Y, where X is a numpy array of dtype uint8 with
        shape (N, 2, height, width) containing pixel values of N pairs and
        Y is a numpy array of dtype float32 with shape (N, 1) containg
        the 'same person'/'different person' information.
    """
    X = np.zeros((len(image_pairs), 2, height, width, IMAGE_CHANNELS),
                 dtype=np.uint8)
    y = np.zeros((len(image_pairs),), dtype=np.float32)

    for i, pair in enumerate(image_pairs):
        X[i] = pair.get_contents(height, width)
        y[i] = Y_SAME if pair.same_person else Y_DIFFERENT

    return X, y

def plot_dataset_skew(pairs_train, pairs_val, pairs_test, only_y_same=True,
                      n_highest=250, show_plot_windows=True,
                      save_to_filepath=None):
    """Draw barcharts showing the number of pictures per person for each
    dataset (train, val, test).

    Each bar in the chart resembles one person and is higher if there are
    more images of that person in the dataset. The bars are ordered descending
    (person with the most images first). Only the first 250 persons are shown.

    A barchart with very unequal bar heights resembles a skewed dataset where
    a small amount of different persons make up most of the images, while a lot
    of other persons in the dataset have barely any images associated with them.

    Args:
        pairs_train: List of pairs of images (ImagePair) of the training
            dataset.
        pairs_val: List of pairs of images (ImagePair) of the validation
            dataset.
        pairs_test: List of pairs of images (ImagePair) of the test dataset.
        only_y_same: Calculate all statistics only for pairs of images showing
            the same person (True). The skew is usually significantly stronger
            for these pairs. (Default is True.)
        n_highest: Limits each bar chart to only the N persons with the highest
            amounts of images in the dataset. (Instead of showing the bars for
            all persons.) (Default is 250.)
        show_plot_windows: Whether to open the plot in a new window. (Default
            is True.)
        save_to_filepath: Full path to a file to which the plot will be saved.
    """
    color = "b" # color of bars (blue)
    bars_width = 0.2

    fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, figsize=(20, 12))
    plt.subplots_adjust(hspace=0.5)

    # Header/Title of the whole plot
    title = "Amount of images per person in each dataset. " \
            "A higher bar means that more images of that person appear in " \
            "the dataset.\n More unequal bar heights means more skew.\n"
    if only_y_same:
        title += "Counts are only based on pairs of images showing the same " \
                 "person. "
    title += "Showing only the %d persons with highest values (per " \
             "dataset)." % (n_highest)
    fig.suptitle(title, fontsize=14)

    def plot_one_chart(ax, pairs, dataset_name, n_highest_legend=15):
        """This subfunction draws the bar chart of one dataset.
        It will be called for training, validation and test dataset.

        Args:
            ax: The matplotlib ax to draw to.
            pairs: List of pairs of images (ImagePair) of the dataset.
            dataset_name: Name of the dataset (subplot title).
            n_highest_legend: Number of people (with highest counts) to show in
                the legend. The legend translates from abbreviated names to
                full names.
        """
        # count the number of images associated with each person
        name_to_images = defaultdict(list)
        for pair in pairs:
            if not only_y_same or (only_y_same and pair.same_person):
                name_to_images[pair.image1.person].append(pair.image1)
                name_to_images[pair.image2.person].append(pair.image2)

        names_with_counts = [(name, len(images)) for name, images in \
                             name_to_images.items()]
        names_with_counts.sort(key=lambda name_with_count: name_with_count[1], \
                               reverse=True)
        names_with_counts = names_with_counts[0:n_highest]
        only_counts = np.array([count for name, count in names_with_counts])

        # estimate the positions of the pairs and the names of the person
        # of each bar
        bars_positions = np.arange(len(names_with_counts))
        bars_names = [name for name, count in names_with_counts]
        # we'll abbreviate names to their capital letters below the x axis
        bars_names_short = [re.sub(r"[^A-Z]", "", name) for name, count \
                            in names_with_counts]
        bars_values = only_counts

        # draw the bars
        ax.bar(bars_positions, bars_values, bars_width, color=color)

        # draw labels for x and y axis, the subplot title and the person names
        # below the x axis
        ax.set_ylabel("Count of images")
        ax.set_xlabel("Person name")
        ax.set_title(dataset_name)

        ax.set_xticks(bars_positions + bars_width)
        ax.set_xticklabels(tuple(bars_names_short), rotation=90,
                           size="x-small")

        # ----
        # create the legend at top right of each chart
        # The legend translates abbreviated names (below x axis) to full names,
        # e.g. "AS = Arnold Schwarzenegger".
        name_translation = zip(bars_names_short, bars_names)
        text_arr1 = [short + "=" + full for (short, full) \
                     in name_translation][0:n_highest_legend]
        text_arr2 = []
        linebreak_every_n = 7
        for i, item in enumerate(text_arr1):
            # add linebreak after 10 names, but not if the name is the
            # last one shown
            if (i+1) % linebreak_every_n == 0 and (i+1) < len(text_arr1):
                text_arr2.append(item + "\n")
            else:
                text_arr2.append(item)
        textstr = " ".join(text_arr2)
        textstr += " (+%d others shown of total %d persons)" \
                   % (max(0, len(bars_names) - n_highest_legend), \
                      len(name_to_images))

        if len(pairs) > 0:
            textstr += " (median=%.1f, mean=%.1f, std=%.2f)" \
                       % (np.median(only_counts), np.mean(only_counts), \
                          np.std(only_counts))
        else:
            textstr += " (median=%.1f, mean=%.1f, std=%.2f)" % (0, 0, 0)

        ax.text(0.3, 0.96, textstr, transform=ax.transAxes, fontsize=8,
                verticalalignment="top", bbox=dict(alpha=0.5))
        # ----

    plot_one_chart(ax1, pairs_train, "Train (%d samples)" % (len(pairs_train)))
    if len(pairs_val) > 0:
        plot_one_chart(ax2, pairs_val, "Validation (%d samples)" \
                       % (len(pairs_val)))
    if len(pairs_test) > 0:
        plot_one_chart(ax3, pairs_test, "Test (%d samples)" \
                       % (len(pairs_test)))

    if save_to_filepath:
        fig.savefig(save_to_filepath)

    if show_plot_windows:
        plt.show()

    plt.close()
