import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.tree.*;

public class BrandingFixV1215 {
    private static final String OWNER = "sgp/client/branding/SgpClientBranding";
    private static final String CLASS = OWNER + ".class";
    private static final String HELPER = "sgp/client/branding/PostCutoverReleaseFinder.class";
    private static final String TOML = "META-INF/neoforge.mods.toml";

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException(
            "usage: BrandingFixV1215 <branding-1.2.14.jar> <helper.class> <out.jar>");
        Path in = Path.of(args[0]), helper = Path.of(args[1]), out = Path.of(args[2]);

        LinkedHashMap<String, byte[]> entries = new LinkedHashMap<>();
        LinkedHashMap<String, JarEntry> meta = new LinkedHashMap<>();
        try (JarFile jf = new JarFile(in.toFile())) {
            Enumeration<JarEntry> en = jf.entries();
            while (en.hasMoreElements()) {
                JarEntry je = en.nextElement();
                if (je.isDirectory()) continue;
                try (InputStream is = jf.getInputStream(je)) {
                    entries.put(je.getName(), is.readAllBytes());
                }
                meta.put(je.getName(), je);
            }
        }

        if (!entries.containsKey(CLASS) || !entries.containsKey(TOML) || entries.containsKey(HELPER))
            throw new IllegalStateException("unexpected Branding 1.2.14 layout");

        String toml = new String(entries.get(TOML), StandardCharsets.UTF_8);
        if (!toml.contains("version=\"1.2.14\""))
            throw new IllegalStateException("expected Branding 1.2.14");
        toml = toml.replace("version=\"1.2.14\"", "version=\"1.2.15\"")
            .replace("stable/test prerelease display, blinking update notice",
                     "legacy/post-cutover stable discovery, blinking update notice");
        entries.put(TOML, toml.getBytes(StandardCharsets.UTF_8));
        entries.put(CLASS, patch(entries.get(CLASS)));
        entries.put(HELPER, Files.readAllBytes(helper));

        Files.deleteIfExists(out);
        try (JarOutputStream jos = new JarOutputStream(Files.newOutputStream(out))) {
            for (var e : entries.entrySet()) {
                JarEntry old = meta.get(e.getKey());
                JarEntry ne = new JarEntry(e.getKey());
                if (old != null && old.getTime() >= 0) ne.setTime(old.getTime());
                else ne.setTime(0L);
                jos.putNextEntry(ne);
                jos.write(e.getValue());
                jos.closeEntry();
            }
        }
    }

    static byte[] patch(byte[] bytes) {
        ClassNode cn = new ClassNode();
        new ClassReader(bytes).accept(cn, 0);
        MethodNode m = cn.methods.stream()
            .filter(x -> x.name.equals("findLatestStableRelease")
                && x.desc.equals("(Ljava/lang/String;)Ljava/lang/String;"))
            .findFirst().orElseThrow();

        m.instructions.clear();
        m.tryCatchBlocks.clear();
        if (m.localVariables != null) m.localVariables.clear();

        InsnList il = new InsnList();
        il.add(new VarInsnNode(Opcodes.ALOAD, 0));
        il.add(new MethodInsnNode(
            Opcodes.INVOKESTATIC,
            "sgp/client/branding/PostCutoverReleaseFinder",
            "find",
            "(Ljava/lang/String;)Ljava/lang/String;",
            false));
        il.add(new InsnNode(Opcodes.ARETURN));
        m.instructions.add(il);
        m.maxLocals = 1;
        m.maxStack = 1;

        ClassWriter cw = new SafeClassWriter(ClassWriter.COMPUTE_FRAMES | ClassWriter.COMPUTE_MAXS);
        cn.accept(cw);
        return cw.toByteArray();
    }

    static final class SafeClassWriter extends ClassWriter {
        SafeClassWriter(int flags) { super(flags); }
        @Override protected String getCommonSuperClass(String a, String b) { return "java/lang/Object"; }
    }
}
