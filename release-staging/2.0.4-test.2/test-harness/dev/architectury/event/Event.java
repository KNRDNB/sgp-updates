package dev.architectury.event;

public final class Event<T> {
    private T listener;

    public void register(T listener) {
        this.listener = listener;
    }

    public T listener() {
        if (listener == null) {
            throw new IllegalStateException("No listener registered");
        }
        return listener;
    }
}
