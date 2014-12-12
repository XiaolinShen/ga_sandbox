#!/usr/bin/env python
import argparse
import time
import json
import pickle
import numpy as np

# Setup GA
from core.algorithm import Algorithm
from core.chromosomes import IntegerChromosome
from core.crossovers import OnePointCrossover
from core.selections import RouletteWheelSelection, TournamentSelection
from core.parallelizer import Parallelizer
from projects.denoising.solution import FilterSequence
from projects.denoising.imaging.char_drawer import CharDrawer
from projects.denoising.imaging.filter_call import FilterCall
import projects.denoising.imaging.noises as noises

# Suppress numpy's FutureWarnings
import warnings
warnings.filterwarnings('ignore')


def get_args():
    parser = argparse.ArgumentParser(
        description='GA experiment'
    )

    # GA params
    parser.add_argument('--population-size',
                        action='store', type=int, default=100)
    parser.add_argument('--elite-size',
                        action='store', type=int, default=10)
    parser.add_argument('--crossover-rate',
                        action='store', type=float, default=0.8)
    parser.add_argument('--selection',
                        action='store', type=str,
                        choices=('roulette', 'tournament'),
                        default='roulette',)
    parser.add_argument('--tournament-size',
                        action='store', type=int, default=0)
    parser.add_argument('--mutation-rate',
                        action='store', type=float, default=0.005)
    parser.add_argument('--chromosome-length',
                        action='store', type=int, default=30)
    parser.add_argument('--fitness-threshold',
                        action='store', type=float, default=0.98)
    parser.add_argument('--max-iterations',
                        action='store', type=int, default=1000)
    parser.add_argument('--rng-freeze',
                        action='store', type=bool, default=False)

    # Filtering params
    parser.add_argument('--noise-type',
                        action='store', type=str,
                        choices=('snp', 'gaussian'),
                        default='snp')
    parser.add_argument('--noise-param',
                        action='store', type=float, default=0.2)

    # Output
    parser.add_argument('--dump-images',
                        action='store', type=bool, default=False)
    parser.add_argument('--output-file',
                        action='store', type=str, default='output.json')
    parser.add_argument('--print-iterations',
                        action='store', type=bool, default=False)

    args = parser.parse_args()
    return args


def run(args):
    if args.rng_freeze is True:
        from core.chromosomes import Chromosome
        from core.crossovers import Crossover
        from core.selections import Selection

        Chromosome._randomizer = np.random.RandomState(0)
        Crossover._randomizer = np.random.RandomState(1)
        Selection._randomizer = np.random.RandomState(2)
        noises._rng_seed = 3

    #---------------------------------------------------------------------------
    # Imaging setup
    #---------------------------------------------------------------------------
    TEXT_COLOR = (0, 0, 0)
    BACKGROUND_COLOR = (255, 255, 255)

    chars = CharDrawer()
    source_image = chars.create_colored_char(
        'A', TEXT_COLOR, BACKGROUND_COLOR)

    # Add noise
    if args.noise_type == 'snp':
        source_image = noises.salt_and_pepper(
            source_image, args.noise_param)
    elif args.noise_type == 'gaussian':
        source_image = noises.gaussian(
            source_image, var=args.noise_param)
    else:
        raise ValueError("Unknown noise type: %s" % args.noise_type)

    # Clean binary target image
    target_image = chars.create_binary_char('A')

    #---------------------------------------------------------------------------
    # GA setup
    #---------------------------------------------------------------------------
    phenotype = FilterSequence(
        genotype=IntegerChromosome(
            length=args.chromosome_length,
            min_val=0,
            max_val=len(FilterCall.all()) - 1),
        source_image=source_image,
        target_image=target_image)

    # Selection
    if args.selection == 'roulette':
        selection = RouletteWheelSelection()
    elif args.selection == 'tournament':
        selection = TournamentSelection(args.tournament_size)
    else:
        raise ValueError("Unknown selection type: %s" % args.selection)

    def calculate_fitness(chromosome):
        individual = phenotype()
        individual.chromosome = chromosome
        return individual._calculate_fitness()
    prepared_tasks = [calculate_fitness]

    with Parallelizer(prepared_tasks) as parallelizer:
        if parallelizer.master_process:
            output = {}
            # Put all parameters into json
            output['parameters'] = {
                'population_size': args.population_size,
                'elite_size': args.elite_size,
                'selection': args.selection,
                'crossover_rate': args.crossover_rate,
                'mutation_rate': args.mutation_rate,
                'chromosome_length': args.chromosome_length,
                'fitness_threshold': args.fitness_threshold,
                'max_iterations': args.max_iterations,
                'noise_type': args.noise_type,
                'noise_param': args.noise_param,
            }
            # Specific type of selection
            if args.selection == 'tournament':
                output['parameters']['tournament_size'] = args.tournament_size

            if args.dump_images is True:
                output['parameters'] += {
                    'source_image_dump': pickle.dumps(source_image),
                    'target_image_dump': pickle.dumps(target_image),
                }

            # Populate during run
            output['iterations'] = []
            output['results'] = {}
            output['parameters']['proc_count'] = parallelizer.proc_count

            solution = None

            # Start GA
            algorithm = Algorithm(
                phenotype=phenotype,
                crossover=OnePointCrossover(args.crossover_rate),
                selection=selection,
                population_size=args.population_size,
                mutation_rate=args.mutation_rate,
                elitism_count=args.elite_size,
                parallelizer=parallelizer)

            # Start counting NOW!
            start = time.time()
            for population, generation in algorithm.run(args.max_iterations):
                # For debugging, mostly
                if args.print_iterations is True:
                    best = population.best_individual.fitness
                    worst = population.worst_individual.fitness
                    average = population.average_fitness
                    solution = population.best_individual
                    print "#%i | best: %f, worst: %f, avg: %f" % (
                        generation, best, worst, average)

                # Write each iteration statistics into output
                iteration_output = {
                    'number': generation,
                    'best_fitness': population.best_individual.fitness,
                    'worst_fitness': population.worst_individual.fitness,
                    'average_fitness': population.average_fitness,
                }
                output['iterations'].append(iteration_output)

                solution = population.best_individual
                if solution.fitness >= args.fitness_threshold:
                    break

            # Time's up
            end = time.time()
            duration = end - start

            # Write results to file
            output['results'] = {
                'solution_dump': pickle.dumps(solution),
                'run_time': duration,
                'iterations': generation,
            }

            with open(args.output_file, 'w') as f:
                json.dump(output, f)

if __name__ == "__main__":
    args = get_args()
    run(args)
