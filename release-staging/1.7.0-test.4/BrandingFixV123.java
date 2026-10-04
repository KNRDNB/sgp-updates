import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.tree.*;

public class BrandingFixV123 {
    private static final String OWNER = "sgp/client/branding/SgpClientBranding";
    private static final String CLASS = OWNER + ".class";
    private static final String LOGO = "assets/sgp_client_branding/textures/gui/sgp_logo.png";

    public static void main(String[] args) throws Exception {
        if (args.length != 3) throw new IllegalArgumentException("usage: BrandingFixV123 <branding-1.2.2.jar> <logo.png> <out.jar>");
        Path in=Path.of(args[0]), logo=Path.of(args[1]), out=Path.of(args[2]);
        LinkedHashMap<String, byte[]> entries=new LinkedHashMap<>();
        LinkedHashMap<String, JarEntry> meta=new LinkedHashMap<>();
        try (JarFile jf=new JarFile(in.toFile())) {
            Enumeration<JarEntry> en=jf.entries();
            while(en.hasMoreElements()) {
                JarEntry je=en.nextElement(); if(je.isDirectory()) continue;
                try(InputStream is=jf.getInputStream(je)){ entries.put(je.getName(),is.readAllBytes()); }
                meta.put(je.getName(),je);
            }
        }
        if(!entries.containsKey(CLASS) || !entries.containsKey(LOGO)) throw new IllegalStateException("unexpected branding 1.2.2 layout");
        String toml=new String(entries.get("META-INF/neoforge.mods.toml"),StandardCharsets.UTF_8);
        if(!toml.contains("version=\"1.2.2\"")) throw new IllegalStateException("expected Branding 1.2.2");
        toml=toml.replace("version=\"1.2.2\"","version=\"1.2.3\"")
            .replace("Persistent title-screen SGP badge with logo, stable/test prerelease version display, blinking update notice and Installer launch button.",
                     "Persistent title-screen SGP badge with clean transparent filtered logo, stable/test prerelease version display, blinking update notice and Installer launch button.");
        entries.put("META-INF/neoforge.mods.toml",toml.getBytes(StandardCharsets.UTF_8));
        entries.put(CLASS,patch(entries.get(CLASS)));
        entries.put(LOGO,Files.readAllBytes(logo));

        Files.deleteIfExists(out);
        try(JarOutputStream jos=new JarOutputStream(Files.newOutputStream(out))) {
            for(var e:entries.entrySet()) {
                JarEntry old=meta.get(e.getKey()), ne=new JarEntry(e.getKey());
                if(old!=null && old.getTime()>=0) ne.setTime(old.getTime());
                jos.putNextEntry(ne); jos.write(e.getValue()); jos.closeEntry();
            }
        }
    }

    static byte[] patch(byte[] bytes) {
        ClassNode cn=new ClassNode(); new ClassReader(bytes).accept(cn,0);
        MethodNode init=cn.methods.stream().filter(x->x.name.equals("onScreenInitPost") && x.desc.equals("(Lnet/neoforged/neoforge/client/event/ScreenEvent$Init$Post;)V")).findFirst().orElseThrow();
        // Refresh authoritative .sgp version on every TitleScreen init. This prevents stale constructor-time
        // state from ever making an older stable release look newer after an Installer update.
        FieldInsnNode packGet=null;
        for(AbstractInsnNode n=init.instructions.getFirst();n!=null;n=n.getNext()) {
            if(n instanceof FieldInsnNode fi && fi.getOpcode()==Opcodes.GETSTATIC && fi.owner.equals(OWNER) && fi.name.equals("packVersion")) { packGet=fi; break; }
        }
        if(packGet==null) throw new IllegalStateException("packVersion init read not found");
        InsnList refresh=new InsnList();
        refresh.add(new MethodInsnNode(Opcodes.INVOKESTATIC,OWNER,"loadPackVersion","()Ljava/lang/String;",false));
        refresh.add(new FieldInsnNode(Opcodes.PUTSTATIC,OWNER,"packVersion","Ljava/lang/String;"));
        init.instructions.insertBefore(packGet,refresh);

        MethodNode m=cn.methods.stream().filter(x->x.name.equals("onScreenRenderPost") && x.desc.equals("(Lnet/neoforged/neoforge/client/event/ScreenEvent$Render$Post;)V")).findFirst().orElseThrow();
        MethodInsnNode blit=null;
        for(AbstractInsnNode n=m.instructions.getFirst();n!=null;n=n.getNext()) {
            if(n instanceof MethodInsnNode mi && mi.getOpcode()==Opcodes.INVOKEVIRTUAL && mi.owner.equals("net/minecraft/client/gui/GuiGraphics") && mi.name.equals("blit") && mi.desc.equals("(Lnet/minecraft/resources/ResourceLocation;IIIFFIIII)V")) {
                if(blit!=null) throw new IllegalStateException("multiple target blits"); blit=mi;
            }
        }
        if(blit==null) throw new IllegalStateException("logo blit not found");
        // Exact 1.2.2 blit tail is x=8,y=10,z=0,u=0,v=0,dst=72x28,tex=72x28.
        List<AbstractInsnNode> vals=new ArrayList<>();
        for(AbstractInsnNode n=blit.getPrevious();n!=null && vals.size()<9;n=n.getPrevious()) if(isValueInsn(n)) vals.add(n);
        Collections.reverse(vals);
        if(vals.size()!=9) throw new IllegalStateException("unexpected logo blit argument shape "+vals.size());
        int[] expected={8,10,0,Integer.MIN_VALUE,Integer.MIN_VALUE,72,28,72,28};
        for(int i=0;i<9;i++) {
            if(i==3||i==4) { if(vals.get(i).getOpcode()!=Opcodes.FCONST_0) throw new IllegalStateException("unexpected float arg "+i); }
            else if(intValue(vals.get(i))!=expected[i]) throw new IllegalStateException("unexpected int arg "+i+" got "+intValue(vals.get(i)));
        }
        m.instructions.set(vals.get(1),intInsn(12));
        m.instructions.set(vals.get(6),intInsn(24));
        m.instructions.set(vals.get(7),intInsn(144));
        m.instructions.set(vals.get(8),intInsn(48));

        // Insert linear filtering immediately before GuiGraphics + texture are pushed for the blit.
        AbstractInsnNode insertBefore=vals.get(0).getPrevious();
        // Walk back over the GETSTATIC LOGO_TEXTURE and ALOAD 3 used by the blit.
        while(insertBefore!=null && (insertBefore.getType()==AbstractInsnNode.LABEL || insertBefore.getType()==AbstractInsnNode.LINE || insertBefore.getType()==AbstractInsnNode.FRAME)) insertBefore=insertBefore.getPrevious();
        if(!(insertBefore instanceof FieldInsnNode fi) || fi.getOpcode()!=Opcodes.GETSTATIC || !fi.owner.equals(OWNER) || !fi.name.equals("LOGO_TEXTURE")) throw new IllegalStateException("logo field prelude not found");
        AbstractInsnNode aload=insertBefore.getPrevious();
        while(aload!=null && (aload.getType()==AbstractInsnNode.LABEL || aload.getType()==AbstractInsnNode.LINE || aload.getType()==AbstractInsnNode.FRAME)) aload=aload.getPrevious();
        if(!(aload instanceof VarInsnNode vi) || vi.getOpcode()!=Opcodes.ALOAD || vi.var!=3) throw new IllegalStateException("GuiGraphics prelude not found");
        InsnList add=new InsnList();
        add.add(new VarInsnNode(Opcodes.ALOAD,2));
        add.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL,"net/minecraft/client/Minecraft","getTextureManager","()Lnet/minecraft/client/renderer/texture/TextureManager;",false));
        add.add(new FieldInsnNode(Opcodes.GETSTATIC,OWNER,"LOGO_TEXTURE","Lnet/minecraft/resources/ResourceLocation;"));
        add.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL,"net/minecraft/client/renderer/texture/TextureManager","getTexture","(Lnet/minecraft/resources/ResourceLocation;)Lnet/minecraft/client/renderer/texture/AbstractTexture;",false));
        add.add(new InsnNode(Opcodes.ICONST_1)); add.add(new InsnNode(Opcodes.ICONST_0));
        add.add(new MethodInsnNode(Opcodes.INVOKEVIRTUAL,"net/minecraft/client/renderer/texture/AbstractTexture","setFilter","(ZZ)V",false));
        m.instructions.insertBefore(aload,add);

        ClassWriter cw=new SafeClassWriter(ClassWriter.COMPUTE_FRAMES|ClassWriter.COMPUTE_MAXS); cn.accept(cw); return cw.toByteArray();
    }
    static boolean isValueInsn(AbstractInsnNode n){ int op=n.getOpcode(); return n instanceof IntInsnNode || n instanceof LdcInsnNode || (op>=Opcodes.ICONST_M1&&op<=Opcodes.ICONST_5) || op==Opcodes.FCONST_0; }
    static int intValue(AbstractInsnNode n){ int op=n.getOpcode(); if(op>=Opcodes.ICONST_M1&&op<=Opcodes.ICONST_5)return op-Opcodes.ICONST_0; if(n instanceof IntInsnNode x)return x.operand; if(n instanceof LdcInsnNode x && x.cst instanceof Integer i)return i; return Integer.MAX_VALUE; }
    static AbstractInsnNode intInsn(int v){ if(v>=-1&&v<=5)return new InsnNode(Opcodes.ICONST_0+v); if(v>=Byte.MIN_VALUE&&v<=Byte.MAX_VALUE)return new IntInsnNode(Opcodes.BIPUSH,v); if(v>=Short.MIN_VALUE&&v<=Short.MAX_VALUE)return new IntInsnNode(Opcodes.SIPUSH,v); return new LdcInsnNode(v); }
    static final class SafeClassWriter extends ClassWriter { SafeClassWriter(int f){super(f);} @Override protected String getCommonSuperClass(String a,String b){return "java/lang/Object";} }
}
