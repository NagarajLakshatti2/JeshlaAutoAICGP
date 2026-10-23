"""Prepare one isolated Playwright Java/TestNG run from inspected locator evidence."""
import hashlib
from pathlib import Path
from urllib.parse import urlparse
from integrations.api.gradle import check_api_pilot_result as check_native_web_result
from integrations.web.text_test import text_input_source
from integrations.web.inspection import validate_public_browser_address
from integrations.web.plans import validate_web_plan

ROOT=Path(__file__).resolve().parents[2]
INIT_SCRIPT=r'''
gradle.projectsEvaluated {
    def p=gradle.rootProject
    def evidenceRoot=new File(System.getProperty('ws9.output'))
    def reportRoot=new File(System.getProperty('ws9.reports'))
    def selectedClass=System.getProperty('ws9.test.class')
    def deps=p.configurations.create('ws9WebPilotDeps')
    p.dependencies.add(deps.name,"com.microsoft.playwright:playwright:${p.ext.playwrightVersion}")
    p.dependencies.add(deps.name,"org.testng:testng:${p.ext.testngVersion}")
    p.dependencies.add(deps.name,"com.fasterxml.jackson.core:jackson-databind:${p.ext.jacksonVersion}")
    def classesFolder=new File(evidenceRoot,'compiled')
    def src=p.sourceSets.create('ws9WebPilot') {
        java.setSrcDirs([new File(p.projectDir,'src/test/java')])
        java.include(selectedClass.replace('.','/')+'.java')
        resources.setSrcDirs([])
        compileClasspath=deps
        runtimeClasspath=output+deps
    }
    p.tasks.named(src.compileJavaTaskName) { options.release=17;destinationDirectory=classesFolder }
    src.output.classesDirs.setFrom(p.files(classesFolder))
    p.tasks.register('ws9WebPilot',Test) {
        dependsOn p.tasks.named(src.classesTaskName)
        testClassesDirs=p.files(classesFolder);classpath=src.runtimeClasspath
        useTestNG();workingDir=evidenceRoot
        include selectedClass.replace('.','/')+'.class'
        ['url','by','target','value','address','dismiss'].each { key ->
            systemProperty 'web.pilot.'+key,System.getProperty('web.pilot.'+key,'')
        }
        systemProperty 'web.pilot.evidence',new File(evidenceRoot,'browser').absolutePath
        systemProperty 'rp.enable','false';systemProperty 'rp.enabled','false'
        environment 'PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD','1'
        reports.junitXml.outputLocation=new File(reportRoot,'xml')
        reports.html.outputLocation=new File(reportRoot,'html')
        binaryResultsDirectory=new File(reportRoot,'binary')
        testLogging {events 'passed','failed','skipped'}
        outputs.upToDateWhen {false}
    }
}
'''


def prepare_web_pilot(tools,output_dir,*,test_class,plan):
    text_input_source(test_class,plan.get("case_id"))
    out=Path(output_dir).resolve()
    if not out.is_relative_to(ROOT/'outputs/acceptance') or out==ROOT/'outputs/acceptance':
        raise ValueError('Choose a dedicated web evidence folder under outputs/acceptance.')
    if plan.get('source_traceability')!='Y' or plan.get('execution_status')!='not_run':
        raise ValueError('A source-checked unexecuted plan is required.')
    if plan.get('locator_by') not in {'label','placeholder'}:
        raise ValueError('Use an exact inspected label or placeholder.')
    for key in ('url','locator_text','test_value','pinned_address'):
        if not isinstance(plan.get(key),str) or not plan[key].strip() or len(plan[key])>1500:
            raise ValueError('Missing bounded web-plan value.')
    url=urlparse(plan['url'])
    if url.scheme!='https' or not url.hostname or url.username or url.password or url.port not in (None,443):
        raise ValueError('Use the inspected public HTTPS origin.')
    validate_public_browser_address(plan['pinned_address'])
    if plan.get('dismiss_button','') not in ('','Decline'):raise ValueError('Only the reviewed cookie refusal action is supported in this pilot.')
    validate_web_plan(tools,plan)
    tools._resolve_file('src/test/java/'+test_class.replace('.','/')+'.java')
    tools._resolve_file('build.gradle')
    out.mkdir(parents=True,exist_ok=True)
    init=out/'web-pilot.init.gradle';init.write_text(INIT_SCRIPT,encoding='utf-8')
    report='build/ws9-web-pilot/'+hashlib.sha256(str(out).encode()).hexdigest()[:12]+'/reports'
    command=['gradlew','--offline','--no-daemon','--console=plain','-I',str(init),'ws9WebPilot',
             '-Dws9.output='+str(out),'-Dws9.reports='+str(tools.root/report),'-Dws9.test.class='+test_class]
    for key,value in {'url':plan['url'],'by':plan['locator_by'],'target':plan['locator_text'],'value':plan['test_value'],
                      'address':plan['pinned_address'],'dismiss':plan.get('dismiss_button','')}.items():
        command.append('-Dweb.pilot.'+key+'='+value)
    return {'command':command,'relative_report_folder':report,'timeout':150}
