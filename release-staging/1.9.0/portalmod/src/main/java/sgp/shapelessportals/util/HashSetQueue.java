package sgp.shapelessportals.util;

import java.util.ArrayDeque;
import java.util.HashSet;

public final class HashSetQueue<T> {
    private final HashSet<T> set = new HashSet<>();
    private final ArrayDeque<T> queue = new ArrayDeque<>();

    public boolean isEmpty() {
        return this.queue.isEmpty();
    }

    public boolean push(T value) {
        if (!this.set.add(value)) {
            return false;
        }
        this.queue.addFirst(value);
        return true;
    }

    public T pop() {
        T value = this.queue.pollLast();
        if (value != null) {
            this.set.remove(value);
        }
        return value;
    }
}
