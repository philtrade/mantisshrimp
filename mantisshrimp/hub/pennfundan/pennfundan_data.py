__all__ = ["get_pennfundan_data"]

from mantisshrimp.imports import *
from mantisshrimp import *


def get_pennfundan_data(force_download=False):
    url = "https://www.cis.upenn.edu/~jshi/ped_html/PennFudanPed.zip"
    # setup file names
    save_dir = get_data_dir() / "PennFudanPed"
    save_dir.mkdir(exist_ok=True)
    zip_file = save_dir / "pennfundan.zip"
    # download and extract data
    if not zip_file.exists():
        download_url(url=url, save_path=zip_file)
        # extract file
        with zipfile.ZipFile(zip_file, "r") as f:
            f.extractall(save_dir)
        # move all extracted files a directory up so they end up at save_dir
        files_dir = save_dir / "PennFudanPed"
        for file in files_dir.ls():
            shutil.move(str(file), save_dir)
        shutil.rmtree(files_dir)

    return save_dir
