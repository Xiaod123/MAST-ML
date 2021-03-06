# How To Mastml

MASTML is written in a fairly modular way, to allow new
sections and subsections to be added without too great of a headache.

There are several places where we have had to _cheat_ and break some of the
rules, but the overall program flow is fairly sensible.

![The structure of do\_combos, I will reference this later](structure.svg)

## `mastml.py`

This is the main entry point to the program, both through the command line or
if calling from within python.  `main` can be called directly with the
appropriate file path, or mastml can be invoked from the command line using

`python -m mastml.mastml foo.conf bar.csv -o results/foobar`

`main` takes in paths to files, relative to your current working directory. If
you need to call mastml without creating files on disk, you need to either
create a `tmp` file (fairly easy) or modify the program to take in file
objects/strings instead (small hassle).

`main` calls `utils.activate_logging` which splits logging across `log.log` and
`errors.log` in `outdir`, as well as printing them to screen. Lower verbosity
causes less to be printed to screen, but does not affect log files.

`mastml_run` is then called inside of a try-catch block, which treats mastml
specific errors differently than errors from other libraries.

#### Conf File Parsing

`mastml_run` calls `conf_parser.parse_conf_file` to convert the conf file into
a conf dict. Notice how these two lines:

```python
PlotSettings = conf['PlotSettings']
is_classification = conf['is_classification']
```

pull two program globals out of the conf dict. All other contents of the conf
dict are used as arguments in other functions. 

#### Data Loading

Here is how we get the entire
input csv, input features, and target features from csv file, saved into pandas
dataframes:

```python
df, X, y = data_loader.load_data(data_path,
                                 conf['GeneralSetup']['input_features'],
                                 conf['GeneralSetup']['target_feature'])
```

`df` has every column except for the `target_feature`, `y` has only the
`target_feature`, and `x` has only the user specified `input_features` 

It's important that `conf` is never passed in it's entirety to anyone who
doesn't need to see it, based in the
[principle of least privilege](http://wiki.c2.com/?PrincipleOfLeastPrivilege).

#### Section Instantiation

Next we get all the instantiation of all of the objects needed to do the
mastml run. This used to look like this before "model snatcher" was added in:
```python
models      = _instantiate(conf['Models'],
                           model_finder.name_to_constructor,
                           'model')
generators  = _instantiate(conf['FeatureGeneration'],
                           feature_generators.name_to_constructor,
                           'featuregenerator')
clusterers  = _instantiate(conf['Clustering'],
                           legos_clusterers.name_to_constructor,
                           'clusterer')
normalizers = _instantiate(conf['FeatureNormalization'],
                           feature_normalizers.name_to_constructor,
                           'featurenormalizer')
selectors   = _instantiate(conf['FeatureSelection'],
                           feature_selectors.name_to_constructor,
                           'featureselector')
splitters   = _instantiate(conf['DataSplits'],
                           data_splitters.name_to_constructor,
                           'datasplit')
```


#### Model Snatcher

Models are instantiated early and passed into feature
selection and learning curve, as specified in those sections. This way, a
subsection can reference a model by name and get its instance and all of its
parameters.

```python
models = _instantiate(conf['Models'],
                      model_finder.name_to_constructor,
                      'model')
models = OrderedDict(models) # for easier modification
_snatch_models(models, conf['FeatureSelection'])
if conf['PlotSettings']['data_learning_curve']:
    name = conf['GeneralSetup']['learning_curve_model']
    conf['GeneralSetup']['learning_curve_model'] = models[name]
    del models[name]
models = list(models.items())
...
```

### Do Combos

This code section processes the data we retrieved using the sections we
instantiated. Its process is the one shown in the diagram at the beginning. The
heptagon shaped sections (Normalization, Selection, DataSplits, Models) do a
"cross product" of their subsections. That is, if you have 2 normalizers, 2 selectors, 2
data splits, and 3 models, you will end up with 8 "combos", each of which runs all 3 models.

For instance, this conf file:
```
[FeatureNormalization]
    [[DoNothing]]
    [[MinMaxScaler]]
        feature_range = 0.1, 0.9

[FeatureSelection]
    [[SelectKBest]]
        k = 5
    [[SelectPercentile]]
        score_func = f_regression
        percentile=20

[DataSplits]
    [[NoSplit]]
    [[KFold]]
        n_splits = 3

[Models]
    [[KNeighborsRegressor]]
    [[GaussianProcessRegressor]]
    [[Ridge]]                       
```

 will branch out like this::

```
.
├── MeanStdevScaler                               
│   ├── SelectKBest                   
│   │   ├── GaussianProcessRegressor
│   │   │   ├── KFold
│   │   │   └── NoSplit
│   │   ├── KNeighborsRegressor
│   │   │   ├── KFold
│   │   │   └── NoSplit
│   │   ├── learning_curve.png
│   │   └── selected.csv
│   └── SelectPercentil
│       ├── GaussianProcessRegressor
│       │   ├── KFold
│       │   └── NoSplit
│       └── KNeighborsRegressor
│           ├── KFold
│           └── NoSplit
└── MinMaxScaler
    ├── SelectKBest
    │   ├── GaussianProcessRegressor
    │   │   ├── KFold
    │   │   └── NoSplit
    │   ├── KNeighborsRegressor
    │   │   ├── KFold
    │   │   └── NoSplit
    │   ├── learning_curve.png
    │   └── selected.csv
    └── SelectPercentile
        ├── GaussianProcessRegressor
        │   ├── KFold
        │   └── NoSplit
        └── KNeighborsRegressor
            ├── KFold
            └── NoSplit
```


## Plots

Plotting is done by invoking the ancient tome "matplotlib" who's sacred runes
strike awe in even the most fearless pythons. 

Plotting is done throughout this process. A plot function should take in some
arrays or dataframe, a `savepath` (or `outdir` for multiple plot outputs), an
optional `title` and sometimes a `stats` `{name: value}` dictionary. You might
see this funny `@ipynb_maker` decorator above most plotting functions. These
cause the code to output a jupyter notebook alongside the corresponding plots
which can reproduce the plots. See `apologies.md` for more details on
`ipynb_maker` and other dirty hacks that require justification.

