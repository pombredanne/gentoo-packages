from django.db import models
from package_info.abstract import AbstractCategory, AbstarctPackage, \
                                  AbstractEbuild
import managers
from package_info.generic import get_from_kwargs_and_del
from package_info.repo_info import REPOS_TYPE
# relative
from .keywords import KeywordRepr

from django.core.validators import URLValidator, validate_email 
from django.core.exceptions import ValidationError

validate_url = URLValidator()

class AbstractDateTimeModel(models.Model):
    created_datetime = models.DateTimeField(auto_now_add = True)
    updated_datetime = models.DateTimeField(auto_now = True)

    class Meta:
        abstract = True

class HomepageModel(models.Model):
    url = models.URLField(max_length=255, unique = True, validators = [validate_url])

    def __unicode__(self):
        return self.url

class ArchesModel(models.Model):
    name = models.CharField(unique = True, max_length = 22, db_index = True)
    
    def __unicode__(self):
        return self.name

class RepositoryModel(AbstractDateTimeModel):
    QUALITY_CHOICES = ( (0, 'stable'),
                        (1, 'testing'),
                        (2, 'experimental'),
                      )

    def __init__(self, *args, **kwargs):
        repo = get_from_kwargs_and_del('repo', kwargs)
        super(RepositoryModel, self).__init__(*args, **kwargs)

        if repo is not None:
            self.init_by_repo(repo)

    name = models.CharField(unique = True, max_length = 60, db_index = True)

    # Additional info
    description = models.TextField(blank = True, null = True)
    owner_name = models.CharField(max_length = 65 , blank = True, null = True)
    owner_email = models.EmailField(blank = True, null = True)
    homepage = models.URLField(blank = True, null = True)
    official = models.BooleanField(default = False)
    quality = models.PositiveSmallIntegerField(choices = QUALITY_CHOICES)

    objects = managers.RepositoryManager()

    def init_by_repo(self, repo):
        self.name = repo.name
        self.update_metadata(repo)

    def update_metadata(self, repo):
        self.description = repo.metadata.description
        self.owner_name = repo.metadata.owner_name
        self.owner_email = repo.metadata.owner_email
        self.homepage = repo.metadata.homepage
        self.official = repo.metadata.official
        self.quality = repo.metadata.int_quality

    def add_related_feeds(self, repo):
        ret = []
        for feed in repo.metadata.feeds:
            ret.append(RepositoryFeedModel(repository = self, feed = feed))

        RepositoryFeedModel.objects.bulk_create(ret)

    def clear_related_feeds(self):
        RepositoryFeedModel.objects.filter(repository = self).delete()

    def update_related_feeds(self, repo):
        self.clear_related_feeds()
        self.add_related_feeds(repo)

    def add_related_sources(self, repo):
        ret = []
        for source in repo.metadata.sources:
            ret.append(RepositorySourceModel(repo_type = source.source_type,
                                             url = source.source_url,
                                             subpath = source.source_subpath,
                                             repository = self))

        RepositorySourceModel.objects.bulk_create(ret)

    def clear_related_sources(self):
        RepositorySourceModel.objects.filter(repository = self).delete()

    def update_related_sources(self, repo):
        self.clear_related_sources()
        self.add_related_sources(repo)

    def add_related(self, repo):
        self.add_related_feeds(repo)
        self.add_related_sources(repo)

    def clear_related(self):
        self.clear_related_feeds()
        self.clear_related_sources()

    def update_related(self, repo):
        self.clear_related()
        self.add_related(repo)

    def __unicode__(self):
        return self.name

class RepositoryFeedModel(models.Model):
    repository = models.ForeignKey(RepositoryModel, db_index = True)
    feed = models.URLField()

    def __unicode__(self):
        return self.feed

    class Meta:
        unique_together = ('repository', 'feed')

class RepositorySourceModel(models.Model):
    REPO_TYPE = REPOS_TYPE.get_as_tuple()

    repo_type = models.PositiveSmallIntegerField(choices = REPO_TYPE)
    url = models.CharField(max_length = 255)
    subpath = models.CharField(max_length = 100, blank = True, null = True)
    repository = models.ForeignKey(RepositoryModel, db_index = True)

    def __unicode__(self):
        return self.url

class CategoryModel(models.Model):
    def __init__(self, *args, **kwargs):
        super(CategoryModel, self).__init__(*args, **kwargs)

        category = kwargs.get('category')
        if isinstance(category, AbstractCategory):  
            self.update_by_category(category)

    def update_by_category(self, category):
        self.description = category.metadata.default_descr
        self.metadata_hash = category.metadata_sha1

    def check_or_need_update(self, category):
        return self.metadata_hash == category.metadata_sha1

    category = models.CharField(unique = True, max_length = 70, db_index = True)
    description = models.TextField(blank = True, null = True)
    metadata_hash = models.CharField(max_length = 128, null = True)
    
    def __unicode__(self):
        return unicode(self.category)

class MaintainerModel(AbstractDateTimeModel):

    def __init__(self, *args, **kwargs):
        maintainer = get_from_kwargs_and_del('maintainer', kwargs)
        super(MaintainerModel, self).__init__(*args, **kwargs)
        if maintainer is not None:
            self.init_by_maintainer(maintainer)
        
    name = models.CharField(max_length = 255, blank = True, null = True)
    email = models.EmailField(unique = True, validators = [validate_email], db_index = True)

    objects = managers.MaintainerManager()

    def init_by_maintainer(self, maintainer):
        self.name = maintainer.name
        self.email = maintainer.email

    def update_by_maintainer(self, maintainer):
        self.name = maintainer.name

    def check_or_need_update(self, maintainer):
        return not (self.name == maintainer.name and \
                    self.email == maintainer.email)
    
    def __unicode__(self):
        return ':'.join((unicode(self.name), self.email))

    class Meta:
        ordering = ('name',)

class HerdsModel(AbstractDateTimeModel):

    def __init__(self, *args, **kwargs):
        herd = get_from_kwargs_and_del('herd', kwargs)
        super(HerdsModel, self).__init__(*args, **kwargs)
        if herd is not None:
            self.init_by_herd(herd)

    name = models.CharField(unique = True, max_length = 150, db_index = True)
    email = models.EmailField(validators = [validate_email])
    description = models.TextField(blank = True, null = True)
    maintainers = models.ManyToManyField(MaintainerModel, blank = True)

    objects = managers.HerdsManager()

    def init_by_herd(self, herd):
        self.name = herd.name
        self.update_by_herd(herd)

    def update_by_herd(self, herd):
        self.email = herd.email
        self.description = herd.description

    def check_or_need_update(self, herd):
        return not (self.name == herd.name and \
                    self.email == herd.email and \
                    self.description == herd.description)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)

class VirtualPackageModel(models.Model):
    name = models.CharField(max_length = 254, db_index = True)
    category = models.ForeignKey(CategoryModel)

    objects = managers.VirtualPackageManager()

    @property
    def cp(self):
        return "%s/%s" % (unicode(self.category), self.name)

    def __unicode__(self):
        return unicode(self.cp)

    class Meta:
        unique_together = ('name', 'category')

class PackageModel(AbstractDateTimeModel):
    def __init__(self, *args, **kwargs):
        package_object, category = \
            get_from_kwargs_and_del(('package','category' ), kwargs)
        
        super(PackageModel, self).__init__(*args, **kwargs)
        if isinstance(package_object, AbstarctPackage):
            self.init_by_package(package_object, category = category)
            
        
    virtual_package = models.ForeignKey(VirtualPackageModel, db_index = True)
    changelog = models.TextField(blank = True, null = True)
    changelog_hash = models.CharField(max_length = 128)
    manifest_hash = models.CharField(max_length = 128)
    metadata_hash = models.CharField(max_length = 128)
    changelog_mtime = models.DateTimeField(blank = True, null = True)
    manifest_mtime = models.DateTimeField(blank = True, null = True)
    mtime = models.DateTimeField(blank = True, null = True)

    herds = models.ManyToManyField(HerdsModel, blank = True)
    maintainers = models.ManyToManyField(MaintainerModel, blank = True)

    description = models.TextField(blank = True, null = True)
    repository = models.ForeignKey(RepositoryModel, db_index = True)
    # Different versions can have different licenses, or homepages.
    
    objects = managers.PackageManager()

    def __unicode__(self):
        return unicode(self.cp)

    @property
    def cp(self):
        return self.virtual_package.cp 

    def init_by_package(self, package, category = None, virtual_package = None):
        #self.name = package.name
        self.update_info(package)
        if virtual_package is None:
            if category is None:
                category, created = CategoryModel \
                    .objects.get_or_create(category = package.category)
            self.virtual_package, created = VirtualPackageModel.objects \
                .get_or_create(name = package.name, category = category)


        elif isinstance(category, CategoryModel):
            self.category = category

    def check_or_need_update(self, package):
        # Need add metadata check to
        return self.manifest_hash != package.manifest_sha1

    def need_update_metadata(self, package):
        return self.metadata_hash != package.metadata_sha1

    def need_update_ebuilds(self, package):
        return self.manifest_hash != package.manifest_sha1

    def update_info(self, package):
        self.mtime = package.mtime
        self.changelog_mtime = package.changelog_mtime
        self.changelog = package.changelog
        self.changelog_hash = package.changelog_sha1
        self.manifest_mtime = package.manifest_mtime
        self.manifest_hash = package.manifest_sha1
        self.metadata_hash = package.metadata_sha1
        self.description = package.description

    def get_ebuilds_and_keywords(self, arch_list):
        l = []
        for ebuild in self.ebuildmodel_set.order_by('-version', '-revision'):
            l.extend(ebuild.get_ebuilds_and_keywords(arch_list))
        return l
            
    class Meta:
        unique_together = ('virtual_package', 'repository')
        ordering = ('-updated_datetime',)

class UseFlagModel(models.Model):
    name = models.CharField(unique = True, max_length = 60, db_index = True)
    description = models.TextField(blank = True)
    
    def __unicode__(self):
        return self.name

class UseFlagDescriptionModel(models.Model):
    use_flag = models.ForeignKey(UseFlagModel, db_index = True)
    package = models.ForeignKey(VirtualPackageModel)
    description = models.TextField()

    def check_or_need_update(self, description):
        return self.description != description 

    def __unicode__(self):
        return unicode(self.use_flag)

    class Meta:
        unique_together = ('use_flag', 'package')

class LicenseModel(models.Model):
    name = models.CharField(unique = True, max_length = 60, db_index = True)
    #description = TextField()
    
    def __unicode__(self):
        return self.name

class LicenseGroupModel(models.Model):
    name = models.CharField(unique = True, max_length = 60, db_index = True)
    licenses = models.ManyToManyField(LicenseModel)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)

class EbuildModel(AbstractDateTimeModel):
    package = models.ForeignKey(PackageModel, db_index = True)
    version = models.CharField(max_length = 26, db_index = True)
    revision = models.CharField(max_length = 12, db_index = True)
    use_flags = models.ManyToManyField(UseFlagModel)
    licenses = models.ManyToManyField(LicenseModel)
    license = models.CharField(max_length = 254, blank = True )
    ebuild_hash = models.CharField(max_length = 128)
    ebuild_mtime = models.DateTimeField(blank = True, null = True)
    is_deleted = models.BooleanField(default = False)
    is_masked = models.BooleanField(default = False)

    homepages = models.ManyToManyField(HomepageModel, blank = True)
    description = models.TextField(blank = True, null = True)

    #eapi = models.PositiveSmallIntegerField(default = 0)
    #slot = models.PositiveSmallIntegerField(default = 0)
    

    objects = managers.EbuildManager()

    def __init__(self, *args, **kwargs ):
        ebuild = get_from_kwargs_and_del('ebuild', kwargs)
        super(EbuildModel, self).__init__(*args, **kwargs)
        if isinstance(ebuild, AbstractEbuild):
            self.init_by_ebuild(ebuild)
        self._prefetched_keywords = None
    
    def __unicode__(self):
        return self.cpv
    
    def init_by_ebuild(self, ebuild):
        self.update_by_ebuild(ebuild)

    def update_by_ebuild(self, ebuild):
        self.is_masked = ebuild.is_masked
        self.version = ebuild.version
        self.revision = ebuild.revision
        self.license = ebuild.license
        self.ebuild_mtime = ebuild.mtime
        self.ebuild_hash = ebuild.sha1
        self.description = ebuild.description

    def check_or_need_update(self, ebuild):
        return self.ebuild_hash != ebuild.sha1

    def init_related(self, ebuild, package = None):
        self.init_by_ebuild(ebuild)
        if package is None:
            self.package = PackageModel.objects.get_or_create(package = ebuild.package)[0]
        elif isinstance(package, PackageModel):
            self.package = package
        self.save()
        l = []
        for license in ebuild.licenses:
            k, created = LicenseModel.objects.get_or_create(name = license)
            if created:
                k.save()
            l.append(k)
        
        self.licenses.add(*l)
        l = []
        # TODO: Bad code
        for use in ebuild.iter_uses():
            k, created = UseFlagModel.objects.get_or_create(name = use)
            if created:
                k.save()
            l.append(k)
        self.use_flags.add(*l)

    def init_with_keywords(self, ebuild):
        self.init_by_ebuild(ebuild)
        l = []
        for keyword in ebuild.iter_keywords():
            ko, created = Keyword.objects.get_or_create(keyword = keyword, ebuild = self)
            if created:
                ko.save()
            l.append(ko)
        self.keyword_set.add(*l)

    @property
    def cp(self):
        return self.package.cp

    @property
    def cpv(self):
        return '%s-%s' % (self.package, self.fullversion) 

    @property
    def fullversion(self):
        return '%s%s' %  (self.version, ('-'+ self.revision if self.revision else ''))

    def get_keywords(self, arch_list):
        keywords_dict = self.get_keywords_dict(arch_list)
        return (KeywordRepr(arch, keywords_dict[arch]) for arch in arch_list)

    def get_keywords_dict(self, arch_list):
        arch_set = set(arch_list)
        keywords_list = self.load_keywords(arch_set)
        keywords_cache_dict = {}
        for keyword in keywords_list:
            keywords_cache_dict[keyword.arch.name] = keyword

        keywords_dict = {}
        keyword_wild = keywords_cache_dict.get('*')
        for arch in arch_list:
            keyword_obj = keywords_cache_dict.get(arch)
            status = -1
            if keyword_obj is not None:
                status = keyword_obj.status
            elif keyword_wild is not None:
                status = keyword_wild.status
            keywords_dict[arch] = status

        return keywords_dict

    def load_keywords(self, arch_set, flush_cache = False):
        if self._prefetched_keywords is None or flush_cache:
            arch_set.add('*')
            self._prefetched_keywords = self.keyword_set. \
                filter(arch__name__in = arch_set).select_related('arch')
        return self._prefetched_keywords

    def get_ebuilds_and_keywords(self, arch_list):
        # Maybe copy object ? !!
        self.keywords = self.get_keywords(arch_list)
        return (self, )

    class Meta:
        unique_together = ('package', 'version', 'revision')
        ordering = ('-updated_datetime',)
        #ordering = ('-updated_datetime', 'package__virtual_package__name',
        #'-version', '-revision')
        
            
class Keyword(models.Model):
    STATUS_CHOICES = (
        (0, 'STABLE'),
        (1, 'NEED TESTING'),
        (2, 'NOT WORK')
    )
    status_repr = ['','~','-']

    ebuild = models.ForeignKey(EbuildModel)
    arch = models.ForeignKey(ArchesModel)
    status = models.PositiveSmallIntegerField(choices = STATUS_CHOICES)

    objects = managers.KeywordManager()

    def __unicode__(self):
        return self.status_repr[self.status] + str(self.arch)
        

    def init_by_keyword(self, keyword, ebuild):
        if isinstance(ebuild, EbuildModel):
            self.ebuild = ebuild
        elif isinstance(ebuild, Ebuild):
            self.ebuild, created = EbuildModel.objects.get_or_create(ebuild = ebuild)
        self.arch, created = ArchesModel.objects.get_or_create(name = keyword.name)
        self.status = keyword.status

    class Meta:
        unique_together = ('ebuild', 'arch')


