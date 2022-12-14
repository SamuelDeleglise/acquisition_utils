from __future__ import annotations
from ..utils import lstrip_int
from ..acquisition_utils import AcquisitionManager, AnalysisManager
from typing import Any, List, Optional
import os

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class AcquisitionNotebookManager(AcquisitionManager):
    """

    ### Init:
    ```
    aqm = AcquisitionNotebookManager("tmp_data/", use_magic=False, save_files=False)
    aqm.set_config_file("configuration.py")
    ```
    ### acquisition_cell:
    ```
    aqm.acquisition_cell('simple_sine')
    ...
    aqm.save_acquisition(x=x, y=y)
    ```

    ### analysis_cell:
    ```
    aqm.analysis_cell()
    ...
    plt.plot(aqm.d.x, aqm.d.y)
    aqm.save_fig()
    ```

    """
    am: Optional[AnalysisManager] = None
    analysis_cell_str = None
    is_old_data = False

    def __init__(self,
                 data_directory: Optional[str] = None, *,
                 config_files: Optional[List[str]] = None,
                 save_files: bool = False,
                 use_magic: bool = False,
                 save_on_edit: bool = True,
                 save_on_edit_analysis: Optional[bool] = None,
                 shell: Any = False):
        """

        Args:
            data_directory (Optional[str], optional):
                Path to data_directory. Should be explicitly set here or as environ parameter.
            config_files (Optional[List[str]], optional):
                List of paths to config files. Defaults to empty.
            save_files (bool, optional):
                True to additionally save config files and the cells to files. Defaults to False.
                So all information is saved inside the h5 file.
            use_magic (bool, optional):
                True to register the magic cells. Defaults to False.
            save_on_edit (bool. Defaults to True):
                True to save data for every change.
            save_on_edit_analysis (bool. Defaults to same as save_on_edit):
                save_on_edit parameter for AnalysisManager i.e. data inside analysis_cell
            shell (InteractiveShell | None, optional. Defaults to False):
                could be provided or explicitly set to None. Defaults to get_ipython().
        """
        if shell is False or shell is True:  # behavior by default shell
            from IPython import get_ipython
            self.shell = get_ipython()
        else:  # if any shell is provided. even None
            self.shell = shell

        if use_magic:
            from .acquisition_magic_class import load_ipython_extension
            load_ipython_extension(aqm=self, shell=self.shell)

        if save_on_edit_analysis is None:
            save_on_edit_analysis = save_on_edit

        self._save_on_edit_analysis = save_on_edit_analysis

        super().__init__(
            data_directory=data_directory,
            config_files=config_files,
            save_files=save_files,
            save_on_edit=save_on_edit)

    @property
    def data(self):
        if self.am is None:
            raise ValueError('No data set')
        return self.am

    @property
    def d(self):
        return self.data

    def save_fig(self, *arg, **kwds):
        if self.am is None:
            raise ValueError('No data set')
        return self.am.save_fig(*arg, **kwds)

    def save_acquisition(self, **kwds):
        super().save_acquisition(**kwds)
        self.load_am()
        return self

    def load_am(self, filename: Optional[str] = None):
        filename = filename or self.current_filepath
        if not os.path.exists(filename.rstrip('.h5') + '.h5'):
            raise ValueError(f"Cannot load data from {filename}")

        self.am = AnalysisManager(
            filename, cell=self.analysis_cell_str,
            save_files=self._save_files, save_on_edit=self._save_on_edit_analysis)

        self.am.unlock_data('useful').update(**{'useful': True}).lock_data('useful')

        if self._save_on_edit_analysis is False:
            self.am.save()

        return self.am

    def acquisition_cell(self, name: str, cell: Optional[str] = None) -> AcquisitionNotebookManager:
        self.analysis_cell_str = None
        self.am = None

        if cell is None and self.shell is not None:
            cell = self.shell.get_parent()['content']['code']  # type: ignore

        self.new_acquisition(name=name, cell=cell)

        logger.info(os.path.basename(self.current_filepath))

        return self

    def analysis_cell(self, filename: Optional[str] = None, cell: Optional[str] = None) -> AcquisitionNotebookManager:
        if cell is None and self.shell is not None:
            cell = self.shell.get_parent()['content']['code']  # type: ignore
            # self.shell.get_local_scope(1)['result'].info.raw_cell  # type: ignore

        if filename:  # getting old data
            self.is_old_data = True
            self.analysis_cell_str = None
            filename = self.get_full_filename(filename)
        else:
            filename = self.current_filepath
            self.is_old_data = False
            self.analysis_cell_str = cell

        logger.info(os.path.basename(filename))

        if os.path.exists(filename.rstrip('.h5') + '.h5'):
            self.load_am(filename)
        else:
            if self.is_old_data:
                raise ValueError(f"Cannot load data from {filename}")
            self.am = None
        return self

    def get_analysis_code(self, look_inside: bool = True) -> str:
        if self.am is None:
            raise ValueError('No data set')

        code = self.am.get('analysis_cell')
        if code is None:
            raise ValueError('There is no field `analysis_cell` inside the data file.')

        # if isinstance(code, bytes):
        #     code = code.decode()

        if look_inside:
            code = code.replace("aqm.analysis_cell()", f"aqm.analysis_cell('{self.am.filepath}')")

        if self.shell is not None:
            self.shell.set_next_input(code)  # type: ignore
        return code

    def get_full_filename(self, filename) -> str:
        if '/' in filename or '\\' in filename:
            return filename

        name_with_prefix = lstrip_int(filename)
        if name_with_prefix:
            suffix = name_with_prefix[1]
            return os.path.join(self.get_data_directory(), suffix, filename)
        return filename

    def parse_config(self, config_name: str = "config"):
        if self.am is None:
            raise ValueError('No data set')

        return self.am.parse_config(config_name)
