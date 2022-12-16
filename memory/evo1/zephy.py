from engine.mathlib import Vec2
from memory.core import LocProcess


class ZephyrosGolemMemory:
    _ROTATION_PTR = [0x20]  # double

    _HP_LEFT_ARM_PTR = [0x48, 0x8, 0x10, 0x18]
    _HP_RIGHT_ARM_PTR = [0x48, 0x8, 0x14, 0x18]
    _HP_ARMOR_PTR = [0x48, 0x8, 0x18, 0x18]
    _HP_CORE_PTR = [0x48, 0x8, 0x1C, 0x18]

    def __init__(self, process: LocProcess, base_ptr: int) -> None:
        self.process = process
        self.base_ptr = base_ptr

        self.rotation_ptr = self.process.get_pointer(
            self.base_ptr, offsets=self._ROTATION_PTR
        )
        # NOTE: These will be invalid and overwritten with something else
        # after the golem phase ends. Don't use once all 3 hp bars are exhausted
        self.hp_left_arm_ptr = self.process.get_pointer(
            self.base_ptr, offsets=self._HP_LEFT_ARM_PTR
        )
        self.hp_right_arm_ptr = self.process.get_pointer(
            self.base_ptr, offsets=self._HP_RIGHT_ARM_PTR
        )
        self.hp_armor_ptr = self.process.get_pointer(
            self.base_ptr, offsets=self._HP_ARMOR_PTR
        )
        self.hp_core_ptr = self.process.get_pointer(
            self.base_ptr, offsets=self._HP_CORE_PTR
        )

    @property
    def rotation(self) -> float:
        return self.process.read_double(self.rotation_ptr)

    @property
    def hp_left_arm(self) -> int:
        return self.process.read_u32(self.hp_left_arm_ptr)

    @property
    def hp_right_arm(self) -> int:
        return self.process.read_u32(self.hp_right_arm_ptr)

    @property
    def hp_armor(self) -> int:
        return self.process.read_u32(self.hp_armor_ptr)

    @property
    def hp_core(self) -> int:
        return self.process.read_u32(self.hp_core_ptr)


class ZephyrosGanonMemory:
    _X_PTR = [0x30]
    _Y_PTR = [0x38]
    _Z_PTR = [0x40]

    _GANON_HP_PTR = [0x5C]

    def __init__(self, process: LocProcess, base_ptr: int) -> None:
        self.process = process
        self.base_ptr = base_ptr

        self.x_ptr = self.process.get_pointer(self.base_ptr, offsets=self._X_PTR)
        self.y_ptr = self.process.get_pointer(self.base_ptr, offsets=self._Y_PTR)
        self.z_ptr = self.process.get_pointer(self.base_ptr, offsets=self._Z_PTR)

        self.ganon_hp_ptr = self.process.get_pointer(
            self.base_ptr, offsets=self._GANON_HP_PTR
        )

    @property
    def pos(self) -> Vec2:
        return Vec2(
            self.process.read_double(self.x_ptr),
            self.process.read_double(self.y_ptr),
        )  # TODO: Z?

    @property
    def hp(self) -> int:
        return self.process.read_u32(self.ganon_hp_ptr)
