import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.tree.*;

public class BrandingPatch {
    private static final String OLD_REGEX = "^v(\\d+)\\.(\\d+)\\.(\\d+)$";
    private static final String NEW_REGEX = "^v(\\d+)\\.(\\d+)\\.(\\d+)(?:-test\\.(\\d+))?$";

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("usage: BrandingPatch <in.jar> <out.jar>");
        Path in = Path.of(args[0]);
        Path out = Path.of(args[1]);
        byte[] targetClass = null;
        LinkedHashMap<String, byte[]> entries = new LinkedHashMap<>();
        LinkedHashMap<String, JarEntry> meta = new LinkedHashMap<>();

        try (JarFile jf = new JarFile(in.toFile())) {
            Enumeration<JarEntry> en = jf.entries();
            while (en.hasMoreElements()) {
                JarEntry je = en.nextElement();
                if (je.isDirectory()) continue;
                byte[] b;
                try (InputStream is = jf.getInputStream(je)) { b = is.readAllBytes(); }
                entries.put(je.getName(), b);
                meta.put(je.getName(), je);
            }
        }

        String clsName = "sgp/client/branding/SgpClientBranding.class";
        targetClass = entries.get(clsName);
        if (targetClass == null) throw new IllegalStateException("missing "+clsName);
        entries.put(clsName, patchClass(targetClass));

        String mods = "META-INF/neoforge.mods.toml";
        String toml = new String(entries.get(mods), java.nio.charset.StandardCharsets.UTF_8);
        if (!toml.contains("version=\"1.2.1\"")) throw new IllegalStateException("unexpected branding version");
        toml = toml.replace("version=\"1.2.1\"", "version=\"1.2.2\"");
        toml = toml.replace(
            "Displays the authoritative pack version from .sgp/pack.json and delegates update download/install to SGP Patch Installer.",
            "Displays the authoritative stable or test prerelease pack version from .sgp/pack.json and delegates update download/install to SGP Patch Installer."
        );
        entries.put(mods, toml.getBytes(java.nio.charset.StandardCharsets.UTF_8));

        Files.deleteIfExists(out);
        try (JarOutputStream jos = new JarOutputStream(Files.newOutputStream(out))) {
            for (Map.Entry<String, byte[]> e : entries.entrySet()) {
                JarEntry old = meta.get(e.getKey());
                JarEntry ne = new JarEntry(e.getKey());
                if (old != null && old.getTime() >= 0) ne.setTime(old.getTime());
                jos.putNextEntry(ne);
                jos.write(e.getValue());
                jos.closeEntry();
            }
        }
    }

    static byte[] patchClass(byte[] input) {
        ClassReader cr = new ClassReader(input);
        ClassNode cn = new ClassNode();
        cr.accept(cn, 0);
        boolean regexPatched = false, comparePatched = false, parsePatched = false;

        for (MethodNode m : cn.methods) {
            if (m.name.equals("<clinit>") && m.desc.equals("()V")) {
                for (AbstractInsnNode n = m.instructions.getFirst(); n != null; n = n.getNext()) {
                    if (n instanceof LdcInsnNode ldc && OLD_REGEX.equals(ldc.cst)) {
                        ldc.cst = NEW_REGEX;
                        regexPatched = true;
                    }
                }
            }
            if (m.name.equals("compareSemVer") && m.desc.equals("(Ljava/lang/String;Ljava/lang/String;)I")) {
                int count = 0;
                for (AbstractInsnNode n = m.instructions.getFirst(); n != null; n = n.getNext()) {
                    if (n.getOpcode() == Opcodes.ICONST_3) {
                        m.instructions.set(n, new InsnNode(Opcodes.ICONST_4));
                        count++;
                    }
                }
                if (count != 1) throw new IllegalStateException("unexpected compareSemVer ICONST_3 count="+count);
                comparePatched = true;
            }
            if (m.name.equals("parseSemVer") && m.desc.equals("(Ljava/lang/String;)[I")) {
                List<AbstractInsnNode> arrayLengths = new ArrayList<>();
                for (AbstractInsnNode n = m.instructions.getFirst(); n != null; n = n.getNext()) {
                    AbstractInsnNode nx = n.getNext();
                    while (nx != null && (nx.getType() == AbstractInsnNode.LABEL || nx.getType() == AbstractInsnNode.LINE || nx.getType() == AbstractInsnNode.FRAME)) nx = nx.getNext();
                    if (n.getOpcode() == Opcodes.ICONST_3 && nx != null && nx.getOpcode() == Opcodes.NEWARRAY) arrayLengths.add(n);
                }
                if (arrayLengths.size() != 2) throw new IllegalStateException("unexpected parseSemVer array-length count="+arrayLengths.size());
                for (AbstractInsnNode n : arrayLengths) m.instructions.set(n, new InsnNode(Opcodes.ICONST_4));

                AbstractInsnNode finalReturn = null;
                for (AbstractInsnNode n = m.instructions.getLast(); n != null; n = n.getPrevious()) {
                    if (n.getOpcode() == Opcodes.ARETURN) { finalReturn = n; break; }
                }
                if (finalReturn == null) throw new IllegalStateException("parseSemVer final ARETURN missing");

                InsnList add = new InsnList();
                add.add(new InsnNode(Opcodes.DUP));
                add.add(new InsnNode(Opcodes.ICONST_3));
                add.add(new VarInsnNode(Opcodes.ALOAD, 1));
                add.add(new InsnNode(Opcodes.ICONST_4));
                add.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL, "java/util/regex/Matcher", "group", "(I)Ljava/lang/String;", false));
                add.add(new LdcInsnNode("2147483647"));
                add.add(new MethodInsnNode(Opcodes.INVOKESTATIC, "java/util/Objects", "requireNonNullElse", "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;", false));
                add.add(new TypeInsnNode(Opcodes.CHECKCAST, "java/lang/String"));
                add.add(new MethodInsnNode(Opcodes.INVOKESTATIC, "java/lang/Integer", "parseInt", "(Ljava/lang/String;)I", false));
                add.add(new InsnNode(Opcodes.IASTORE));
                m.instructions.insertBefore(finalReturn, add);
                m.maxStack = Math.max(m.maxStack, 4);
                parsePatched = true;
            }
        }
        if (!regexPatched || !comparePatched || !parsePatched)
            throw new IllegalStateException("patch incomplete regex="+regexPatched+" compare="+comparePatched+" parse="+parsePatched);

        ClassWriter cw = new ClassWriter(0);
        cn.accept(cw);
        return cw.toByteArray();
    }
}
