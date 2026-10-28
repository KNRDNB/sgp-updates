package dev.architectury.event;

public final class EventFactory {
    private EventFactory() {}

    public static Event<Object> create() {
        return new EventImpl<>();
    }

    private static final class EventImpl<T> implements Event<T> {
        private T last;

        @Override
        public void register(T listener) {
            last = listener;
        }

        Object last() {
            return last;
        }
    }
}
