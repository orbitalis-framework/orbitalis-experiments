# Orbitalis Experiments

## Development

### Install

#### Devcontainer (suggested)

1. Install [Docker](https://www.docker.com/)
2. Install Devcontainer extension from VSCode marketplace
3. Click bottom-most-left button and re-open this directory in container

**NOTE**: devcontainer was setup to use system Python 3.12, please select it using bottom-most-right button.

#### Bare-metal

1. Install requirements

```
pip install -r requirements.txt
```

2. Install MQTT broker


## Evaluation

Experiments are based on containers. In particular we use cAdvisor and Prometheus to measure resources consumption and we have built our container to run single experiment. You can modify configuration in `docker-compose.yml`

Following scripts used to run experiments:

```
run_experiments.sh
```

```
run_experiments_by_pairs.sh
```

```
run_experiments_by_combinations.sh
```



## Plot Results

In order to plot results, we have built a CLI: `plot.py`

Instead, to visualize discovery overhead: `evaluate_discovery.py`
