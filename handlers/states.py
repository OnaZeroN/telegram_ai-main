
class StateCustom:
    state = 'main'
    states = {}

    def set_state(self, user_key: str, state: str):
        self.states[user_key] = state

    def get_state_and_prefix(self, user_key: str) -> tuple:
        state = self.states.get(user_key)
        prefix = ''
        if state == 'doc':
            prefix = '📄'
        elif state is None:
            self.set_state(user_key, 'main')
            return self.get_state_and_prefix(user_key)
        return state, prefix
