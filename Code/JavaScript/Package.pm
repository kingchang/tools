package JavaScript::Package;

use defaults;
use File::Spec ();
use Graph::Directed ();
use Moose;
use MooseX::Types::Path::Class ();
use Throwable::Error ();

use JavaScript::File ();
use JavaScript::Module ();
use JavaScript::TestSuite ();


has path =>,
    is => 'ro',
    isa => 'Path::Class::Dir',
    default => File::Spec->curdir,
    coerce => $true;


# --- Instance ---

sub dependencies {
    my ($self) = @ARG;
    my $suffix = JavaScript::File->suffix;
    my @files = map {JavaScript::File->new(path => $ARG)}
        grep {!$ARG->is_dir() && ($ARG->basename =~ m/\Q$suffix\E$/)}
        $self->path->children(no_hidden => $true);
    
    my %files = map {($ARG->full_name => $ARG)} @files;
    my $dependencies = Graph::Directed->new;
    
    foreach my $file (@files) {
        foreach my $requirement ($file->requires) {
            my $required_file = $files{$requirement};
            
            unless (defined $required_file) {
                Throwable::Error->throw(
                    sprintf 'Requirement not found: %s <- %s',
                        $requirement, $file->full_name);
            }
            
            $dependencies->add_edge($required_file, $file);
        }
        
        if ($file->is_test) {
            $dependencies->add_edge($files{$file->name}, $file);
        }
    }
    
    return $dependencies;
}


sub modules {
    my ($self) = @ARG;
    my $dependencies = $self->dependencies;
    my %modules;
    
    foreach my $file ($dependencies->topological_sort) {
        my @dependencies = map {$modules{$ARG->full_name}}
            $dependencies->all_predecessors($file);
        
        $modules{$file->full_name} = JavaScript::Module->new(
            dependencies => \@dependencies,
            file => $file);
    }
    
    return sort {@{$a->dependencies} <=> @{$b->dependencies}} values %modules;
}


sub test_suite {
    my ($self) = @ARG;
    my (@tests, @implementations);
    
    foreach my $module ($self->modules) {
        if ($module->file->is_test) {
            push @tests, $module;
        }
        else {
            push @implementations, $module;
        }
    }
    
    return JavaScript::TestSuite->new(
        implementations => \@implementations,
        tests => \@tests);
}
