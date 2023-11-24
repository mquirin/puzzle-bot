"""
Prank mode:
- ignores pieces with no matches
- Tries flipping pieces to see if they'll have matches
"""
import cProfile
import argparse
import os
import time
import multiprocessing
import re

from common import board, connect, segment, util, vector


INPUT_DIR = '0_input'
SEGMENT_DIR = '1_prank'
FLIP_SEGMENT_DIR = '1_flip'
VECTOR_DIR = '2_vector'
CONNECTIVITY_DIR = '3_connectivity'
SOLUTION_DIR = '4_solution'


def solve(path, width, height, serialize, id, skip_step, stop_step):
    start_time = time.time()

    for i, d in enumerate([INPUT_DIR, SEGMENT_DIR, VECTOR_DIR, CONNECTIVITY_DIR, SOLUTION_DIR]):
        os.makedirs(os.path.join(path, d), exist_ok=True)

        # wipe any directories we'll act on, except 0 which is the input
        if i != 0 and i > skip_step + 1 and i < stop_step:
            for f in os.listdir(os.path.join(path, d)):
                os.remove(os.path.join(path, d, f))

    if skip_step < 0 and stop_step > 0:
        segment_each(input_path=os.path.join(path, INPUT_DIR), output_path=os.path.join(path, SEGMENT_DIR), id=id)

    if skip_step < 1 and stop_step > 1:
        start_id = flip_each(input_path=os.path.join(path, SEGMENT_DIR), output_path=os.path.join(path, FLIP_SEGMENT_DIR))
        vectorize(input_path=os.path.join(path, SEGMENT_DIR), output_path=os.path.join(path, VECTOR_DIR), id=id, serialize=serialize)
        vectorize(input_path=os.path.join(path, FLIP_SEGMENT_DIR), output_path=os.path.join(path, VECTOR_DIR), id=id, serialize=serialize, start_id=start_id)

    if skip_step < 2 and stop_step > 2:
        find_connectivity(input_path=os.path.join(path, VECTOR_DIR), output_path=os.path.join(path, CONNECTIVITY_DIR), id=id, serialize=serialize)

    if skip_step < 3 and stop_step > 3 and not id:
        build_board(width, height, input_path=os.path.join(path, CONNECTIVITY_DIR), output_path=os.path.join(path, SOLUTION_DIR))

    print('')

    duration = time.time() - start_time
    print(f"\n{util.GREEN}### Puzzle solved in {round(duration, 2)} sec ###{util.WHITE}\n")


def flip_each(input_path, output_path):
    """
    Loads each image in the input directory, segments it into a black & white bitmap in the output directory
    """
    print(f"\n{util.RED}### Flipping ###{util.WHITE}\n")

    out_id = 1
    while os.path.exists(os.path.join(input_path, f'{out_id}.bmp')):
        out_id += 1

    start_time = time.time()
    start_id = out_id
    i = 1
    while os.path.exists(os.path.join(input_path, f'{i}.bmp')):
        input_img_path = os.path.join(input_path, f'{i}.bmp')
        output_img_path = os.path.join(output_path, f'{out_id}.bmp')
        print(f"> Flipping image {input_img_path} into {output_img_path}")
        segment.flip(input_img_path, output_img_path)
        i += 1
        out_id += 1

    duration = time.time() - start_time
    print(f"Flipping took {round(duration, 2)} seconds ({round(duration/i, 2)} seconds per image)")
    return start_id


def segment_each(input_path, output_path, id):
    """
    Loads each image in the input directory, segments it into a black & white bitmap in the output directory
    """
    print(f"\n{util.RED}### Segmenting ###{util.WHITE}\n")

    start_time = time.time()
    i = id if id is not None else 1
    with multiprocessing.Pool(processes=os.cpu_count()) as pool:
        results = []
        while os.path.exists(os.path.join(input_path, f'{i}.jpeg')):
            input_img_path = os.path.join(input_path, f'{i}.jpeg')
            output_img_path = os.path.join(output_path, f'{i}.bmp')
            print(f"> Segmenting image {input_img_path} into {output_img_path}")
            results.append(pool.apply_async(segment.segment, (input_img_path, output_img_path)))

            i += 1
            if id is not None:
                break

        for r in results:
            r.get()

    duration = time.time() - start_time
    print(f"Segmenting took {round(duration, 2)} seconds ({round(duration/i, 2)} seconds per image)")


def vectorize(input_path, output_path, id, serialize, start_id=1):
    """
    Loads each image.bmp in the input directory, converts it to an SVG in the output directory
    """
    print(f"\n{util.RED}### Vectorizing ###{util.WHITE}\n")

    start_time = time.time()
    i = id if id is not None else start_id

    args = []
    while os.path.exists(os.path.join(input_path, f'{i}.bmp')):
        path = os.path.join(input_path, f'{i}.bmp')
        render = (i == id)
        args.append([path, i, output_path, render])

        i += 1
        if id is not None:
            break

    if serialize:
        for arg in args:
            vector.load_and_vectorize(arg)
    else:
        with multiprocessing.Pool(processes=os.cpu_count()) as pool:
            pool.map(vector.load_and_vectorize, args)

    duration = time.time() - start_time
    print(f"Vectorizing took {round(duration, 2)} seconds ({round(duration /i, 2)} seconds per piece)")


def find_connectivity(input_path, output_path, id, serialize):
    """
    Opens each piece data and finds how each piece could connect to others
    """
    print(f"\n{util.RED}### Building connectivity ###{util.WHITE}\n")
    start_time = time.time()
    connect.build(input_path, output_path, id, serialize)
    duration = time.time() - start_time
    print(f"Building the graph took {round(duration, 2)} seconds")


def build_board(width, height, input_path, output_path):
    """
    Searches connectivity to find the solution
    """
    print(f"\n{util.RED}### Build board ###{util.WHITE}\n")
    start_time = time.time()
    board.build(width, height, input_path, output_path)
    duration = time.time() - start_time
    print(f"Building the board took {round(duration, 2)} seconds")


def rename(path):
    d = os.path.join(path, INPUT_DIR)

    # for each file in this directory, rename it to i.jpeg
    i = 1

    # only rename jpg or jpeg
    previous_files = [f for f in os.listdir(d) if re.match(r'.*\.jpe?g', f)]
    print(f"There are {len(previous_files)} files to rename")

    for f in previous_files:
        src = os.path.join(d, f)
        dest = os.path.join(d, f'{i}.jpeg.tmp')
        os.rename(src, dest)
        i += 1

    i = 1
    for f in previous_files:
        src = os.path.join(d, f'{i}.jpeg.tmp')
        dest = os.path.join(d, f'{i}.jpeg')
        os.rename(src, dest)
        i += 1
    print(f"Renamed {len(previous_files)} files")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', help='Path to the base directory that has a dir `0_input` full of JPEGs in it')
    parser.add_argument('--only-process-id', default=None, required=False, help='Only processes the provided ID', type=int)
    parser.add_argument('--skip-step', default=-1, required=False, help='Start processing from after this step', type=int)
    parser.add_argument('--stop-at-step', default=10, required=False, help='Stop processing at this step', type=int)
    parser.add_argument('--serialize', default=False, action="store_true", help='Single-thread processing')
    parser.add_argument('--rename', default=False, action="store_true", help='Renames the input files to 1.jpeg, 2.jpeg, ...')
    parser.add_argument('--width', required=True, help='Width of the puzzle in pieces', type=int)
    parser.add_argument('--height', required=True, help='Width of the puzzle in pieces', type=int)
    args = parser.parse_args()

    if args.rename:
        rename(path=args.path)

    solve(path=args.path, width=args.width, height=args.height, serialize=args.serialize, id=args.only_process_id, skip_step=args.skip_step, stop_step=args.stop_at_step)


if __name__ == '__main__':
    PROFILE = False
    if PROFILE:
        cProfile.run('main()', 'profile_results.prof')
    else:
        main()
