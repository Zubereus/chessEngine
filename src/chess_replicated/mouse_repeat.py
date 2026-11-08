class MouseHoldRepeater:
    def __init__(self, initial_delay=350, interval=75):
        self.initial_delay = initial_delay
        self.interval = interval
        self.next_repeat_at = None

    def start(self, now):
        self.next_repeat_at = now + self.initial_delay

    def stop(self):
        self.next_repeat_at = None

    def update(self, now, held):
        if not held:
            self.stop()
            return 0
        if self.next_repeat_at is None:
            return 0

        if now < self.next_repeat_at:
            return 0

        repeats = (now - self.next_repeat_at) // self.interval + 1
        self.next_repeat_at += repeats * self.interval
        return repeats
