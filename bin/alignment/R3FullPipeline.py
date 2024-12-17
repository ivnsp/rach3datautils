"""
Script that handles full preprocessing of Rach3 dataset for use with ML.
"""

import argparse as ap
import os
import tempfile
from pathlib import Path

from tqdm import tqdm

from rach3datautils.alignment.extract_and_concat import extract_and_concat
from rach3datautils.alignment.split import split_video_flac_mid
from rach3datautils.utils.dataset import DatasetUtils

parser = ap.ArgumentParser(
    prog="Audio Alignment Pipeline",
    description="To be used with rach3 dataset. Performs multiple steps "
                "in the audio alignment pipeline."
)
parser.add_argument(
    "-d", "--root_dir",
    action='store',
    help='The root directory where the dataset is located. All folders '
         'and subfolders in this directory will be searched.',
    nargs="*",
    required=True
)
parser.add_argument(
    "-w", "--overwrite",
    action='store_true',
    help='Whether to overwrite any already existing files in the '
         'locations specified.'
)
parser.add_argument(
    "-o", "--output_dir", action='store',
    help='Where to output processed files. If the directory does not '
         'exist, a new one will be created. Output directory must be '
         'within the input directory.',
    default='./processed_audio'
)
parser.add_argument(
    "-r", "--reencode", action='store_true',
    help='Whether to reencode the concatonated video for more accurate '
         'timestamps.'
)
args = parser.parse_args()


output_dir = Path(args.output_dir)

if output_dir.suffix:
    raise AttributeError("output_dir should be a directory")
if not output_dir.exists():
    os.mkdir(output_dir)

with tempfile.TemporaryDirectory(dir="../") as tempdir:
    tempdir = Path(tempdir)

    dataset = DatasetUtils(root_path=args.root_dir + [tempdir])
    sessions = dataset.get_sessions([".mp4", ".mid", ".flac", ".aac"])
    sessions = dataset.remove_noncomplete(
        sessions,
        required=["video.file_list", "midi.file", "flac.file"]
    )

    processed = list()
    print(f"Found {len(sessions)} sessions:")
    for i in sessions:
        print(i.id)
    print("Processed sessions will be listed in processed_sessions.txt in the output directory.")
    if not os.path.exists(output_dir / "processed_sessions.txt"):
        with open(output_dir / "processed_sessions.txt", "w") as f:
            f.write("")

    for subsession in tqdm(sessions, desc="running full pipeline"):
        print(f"Processing session: {subsession.id}")
        try:
            if subsession.audio.file is None or subsession.video.file is None:
                concat_outputs = extract_and_concat(
                    session=subsession,
                    output=tempdir,
                    overwrite=args.overwrite,
                    reencode=args.reencode
                )
            [subsession.set_unknown(i) for i in concat_outputs]
            split_video_flac_mid(
                midi=subsession.midi.file,
                flac=subsession.flac.file,
                audio=subsession.audio.file,
                performance=subsession.performance,
                video=subsession.video.file,
                output_dir=output_dir,
                overwrite=args.overwrite
            )
            [i.unlink() for i in concat_outputs]
            print(f"{subsession.id} processed successfully.")
            processed.append(str(subsession.id))
        except Exception as e:
            print(f"Error processing {subsession.id}: {e}")
            continue


# save list of processed sessions to a file
with open(output_dir / "processed_sessions.txt", "a") as f:
    f.write("\n".join(processed))

print(f"Successfully processed files to: {output_dir.absolute()}")
