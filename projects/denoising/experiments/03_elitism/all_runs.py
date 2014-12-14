#!/usr/bin/env python
import os
import sys
from bunch import bunchify
from projects.denoising.experiments import experiment


def all_runs(result_dir):
    args = {
        'population_size': 100,
        'elite_size': 0,
        'selection': 'roulette',
        'tournament_size': 0,
        'crossover_rate': 0.8,
        'mutation_rate': 0.005,
        'chromosome_length': 30,
        'fitness_threshold': 0.98,
        'max_iterations': 1000,
        'rng_freeze': False,

        'noise_type': 'snp',
        'noise_param': 0.2,

        'dump_images': False,
        'output_file': 'output.json',
        'print_iterations': False,
    }

    # One run for each elitism value
    pid = os.getpid()
    for elite_size in xrange(1, 100):
        output_filename = "elite-%i-%i.json" % elite_size % pid
        filepath = os.path.join(result_dir, output_filename)
        args['output_file'] = filepath
        args['elite_size'] = elite_size
        experiment.run(bunchify(args))

if __name__ == "__main__":
    rel_dir = sys.argv[1]
    abs_dir = os.path.abspath(rel_dir)
    if not os.path.exists(abs_dir):
        os.makedirs(abs_dir)
    all_runs(abs_dir)