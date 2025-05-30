import itertools

token_iter = itertools.count()

class CaseEntity:
    """
    A class representing a case entity in the simulation.
    """

    id_iter = itertools.count()

    def __init__(self, id=None):
        if id is None:
            self.id = next(CaseEntity.id_iter)
        else:
            self.id = id

        self.token_id = self.id

        self.type = 0
        self.specimen_containers = 1
        self.specimen_type = None

        self.blocks = []
        self.slides = []

        self.scanned_slides = 0
        self.stainingIHC = False

        self.start_time = None
        self.finish_time = None
        self._sent_to_final = False

class BlockEntity(CaseEntity):
    """
    A class representing a tissue block derived from a case.
    """
    def __init__(self, parent_case: CaseEntity):
        super().__init__(id=parent_case.id)
        self.token_id = next(token_iter)
        self.type = 2
        self.parent_case = parent_case
        self.specimen_type = parent_case.specimen_type
        self.slides = []
        parent_case.blocks.append(self)

class SlideEntity(CaseEntity):
    """
    A class representing a slide derived from a block.
    """
    def __init__(self,parent_case: CaseEntity, parent_block: BlockEntity = None):
        super().__init__(id=parent_case.id)
        self.token_id = next(token_iter)
        self.type = 3

        self.parent_block = parent_block
        self.parent_case = parent_case

        self.process_count = 0
        self.specimen_type = parent_case.specimen_type

        parent_case.slides.append(self)
        if parent_block is not None:
            parent_block.slides.append(self)

