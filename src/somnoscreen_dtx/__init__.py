"""Read SOMNOscreen plus raw recordings (DATEN1.DTX + konfig.dt2) and convert them to EDF."""
from .dtx import POSITIONS, Recording, Signal, UnsupportedMontage, read_dtx
from .edf import write_edf
from .konfig import Konfig, read_konfig

__version__ = '0.1.0'
__all__ = ['POSITIONS', 'Konfig', 'Recording', 'Signal', 'UnsupportedMontage', 'read_dtx',
           'read_konfig', 'write_edf']
