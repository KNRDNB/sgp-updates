import java.io.*;
import java.util.jar.*;
import jdk.internal.org.objectweb.asm.*;
import jdk.internal.org.objectweb.asm.tree.*;
import jdk.internal.org.objectweb.asm.tree.analysis.*;

public class AsmVerify {
  public static void main(String[] args) throws Exception {
    try (JarFile jf = new JarFile(args[0])) {
      byte[] b = jf.getInputStream(jf.getJarEntry("sgp/client/branding/SgpClientBranding.class")).readAllBytes();
      ClassNode cn = new ClassNode();
      new ClassReader(b).accept(cn, 0);
      for (MethodNode m : cn.methods) {
        Analyzer<BasicValue> a = new Analyzer<>(new BasicVerifier());
        try { a.analyze(cn.name, m); }
        catch (AnalyzerException e) { throw new RuntimeException("ASM verify failed in "+m.name+m.desc, e); }
      }
      System.out.println("ASM BASIC VERIFY: PASS methods="+cn.methods.size());
    }
  }
}
