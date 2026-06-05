class ActionSpace:
    LEARN_MAC      = 0
    EVICT_ENTRY    = 1
    FLOOD          = 2
    BLOCK_PORT     = 3
    UNBLOCK_PORT   = 4
    INCREASE_AGING = 5
    DECREASE_AGING = 6

    @staticmethod
    def get_all_actions():
        return [0, 1, 2, 3, 4, 5, 6]

    @staticmethod
    def get_action_name(action_idx):
        names = {
            0: 'LEARN_MAC',
            1: 'EVICT_ENTRY',
            2: 'FLOOD',
            3: 'BLOCK_PORT',
            4: 'UNBLOCK_PORT',
            5: 'INCREASE_AGING',
            6: 'DECREASE_AGING'
        }
        return names.get(action_idx, 'UNKNOWN')

    @staticmethod
    def get_action_count():
        return 7