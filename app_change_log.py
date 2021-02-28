#!venv/bin/python

import json
import os
import sys

CHANGE_LOG_PATH = "change_log.json"


def clear():
    if os.name =='posix':
        _ = os.system('clear')
    else:
        print("Clear command was not defined for this platform.")


class AppChangeLog():
    def __init__(self, interactive=False):
        self.interactive = interactive
        if os.path.exists(CHANGE_LOG_PATH):
            with open(CHANGE_LOG_PATH, 'r') as file:
                self.changes = json.loads(file.read())
        else:
            self.changes = []

    def new_change(self):
        if self.interactive:
            return
        print("Next build version?")
        build_version = input()
        major, minor, patch, build = build_version.split('.')
        clear()
        levels = ['Major', 'Minor', 'Patch', 'Build']
        level = 0
        changes = []
        outer = True
        while outer:
            change_list = []
            while True:
                print(f'{levels[level]} changes: (A)dd, (D)elete, (N)ext level, (E)nd')
                command = input().lower()
                if command == 'a':
                    print("Add your change:")
                    new_change = input()
                    change_list.append(new_change)
                elif command == 'd':
                    print("Which change do you want to delete? Enter index or (N)one")
                    for i, change in enumerate(change_list):
                        print(f'({i}): {change[:50]}')
                    delete_command = input().lower()
                    if delete_command.isnumeric():
                        del change_list[int(delete_command)]
                elif command == 'n':
                    break
                elif command == 'e':
                    outer = False
                    break
                    
                else:
                    print("Invalid command")

            changes.append(change_list)
            level += 1
            if level == len(levels):
                outer = False
        
        new_change = {'version': build_version, 'major': major, 'minor': minor, 'patch': patch, 'build': build}
        for i, l in enumerate(levels):
            level_change = [] if i >= len(changes) else changes[i]
            new_change[f'{l.lower()}_changes'] = level_change
            
        self.changes.insert(0, new_change)
        with open(CHANGE_LOG_PATH, 'w') as file:
            file.write(json.dumps(self.changes))

    def print(self):
        if self.interactive:
            return
        start_view = 0
        view_size = 5       
        while True:
            up = start_view > 0
            down = start_view + view_size < len(self.changes)
            if up:
                print('(U)p')
            for i, change in enumerate(self.changes[start_view:start_view + view_size]):
                print(f'({i + 1}){start_view + i + 1}: {change["version"]}')
            if down:
                print('(D)own')
            print("(Q)uit print view")

            command = input().lower()
            clear()
            if command.isnumeric():
                self.print_change(int(command) + start_view - 1)
                break
            elif up and command == 'u':
                start_view = max(start_view - view_size, 0)
            elif down and command == 'd':
                start_view = min(start_view + view_size, len(self.changes) - view_size)
            elif command == 'q':
                break

    def delete(self):
        if self.interactive:
            return
        start_view = 0
        view_size = 5       
        while True:
            up = start_view > 0
            down = start_view + view_size < len(self.changes)
            if up:
                print('(U)p')
            for i, change in enumerate(self.changes[start_view:start_view + view_size]):
                print(f'({i + 1}){start_view + i + 1}: {change["version"]}')
            if down:
                print('(D)own')
            print("(Q)uit delete menu")

            command = input().lower()
            clear()
            if command.isnumeric():
                del self.changes[int(command) + start_view - 1]
                break
            elif up and command == 'u':
                start_view = max(start_view - view_size, 0)
            elif down and command == 'd':
                start_view = min(start_view + view_size, len(self.changes) - view_size)
            elif command == 'q':
                break
                
            with open(CHANGE_LOG_PATH, 'w') as file:
                file.write(json.dumps(self.changes))
        

    def print_change(self, i):
        if self.interactive:
            return
        print(f'Build Version: {self.changes[i]["version"]}')
        print(f'Major Changes:')
        print(''.join([f'\t-{change}\n' for change in self.changes[i]['major_changes']]))
        print(f'Minor Changes:')
        print(''.join([f'\t-{change}\n' for change in self.changes[i]['minor_changes']]))
        print(f'Patch Changes:')
        print(''.join([f'\t-{change}\n' for change in self.changes[i]['patch_changes']]))
        print(f'Build Changes:')
        print(''.join([f'\t-{change}\n' for change in self.changes[i]['build_changes']]))

        while True:
            print('(P)revious, (N)ext, (Q)uit')
            command = input().lower()
            clear()
            if command == 'n':
                if i + 1 >= len(self.changes):
                    print("Invalid change index")
                else:
                    self.print_change(i + 1)
            if command == 'p':
                if i - 1 < 0:
                    print("Invalid change index")
                else:
                    self.print_change(i - 1)
            elif command == 'q':
                break
            else:
                print("Invalid command")

    def quit(self):
        if self.interactive:
            return
        with open(CHANGE_LOG_PATH, 'w') as file:
            file.write(json.dumps(self.changes))


    def get_since(self, build_version):
        return list(filter(lambda a: build_version_sort(a['version'], build_version) > 0, self.changes))


def build_version_sort(a, b, version=True):
    if version:
        a_version = a
        b_version = b
    else:
        a_version = a['version']
        b_version = b['version']

    major_a, minor_a, patch_a, build_a = a_version.split('.')
    major_b, minor_b, patch_b, build_b = b_version.split('.')

    if major_a != major_b:
        return int(major_a) - int(major_b)
    elif minor_a != minor_b:
        return int(minor_a) - int(minor_b)
    elif patch_a != patch_b:
        return int(patch_a) - int(patch_b)
    return int(build_a) - int(build_b)


def main():
    changelog = AppChangeLog()
    while True:
        print("Valid commands: (P)rint, (N)ew, (C)lear, (G)et changes, (D)elete, (Q)uit\nEnter a command:")
        command = input().lower()
        if command == 'p':
            changelog.print()
        elif command == 'n':
            changelog.new_change()
        elif command == 'd':
            changelog.delete()
        elif command == 'g':
            print("Which build version do you want to get items since?")
            build_version = input()
            print(changelog.get_since(build_version))
        elif command == 'q':
            print("Quitting")
            changelog.quit()
            break
        elif command == 'c':
            clear()
    

if __name__ == '__main__':
    main()